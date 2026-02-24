"""
CORTEX v5.1 — Admin & Governance Router.

High-privilege endpoints for project management, API key governance,
and session handoff orchestration. Enforces strict RBAC and input validation.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

import cortex.api.state as api_state
from cortex import __version__
from cortex.api.deps import get_engine
from cortex.auth import AuthResult, get_auth_manager, require_permission
from cortex.engine import CortexEngine
from cortex.types.models import StatusResponse
from cortex.utils.export import export_facts
from cortex.utils.i18n import DEFAULT_LANGUAGE, get_trans

__all__ = [
    "create_api_key",
    "export_project",
    "generate_handoff_context",
    "get_system_status",
    "list_api_keys",
]

router = APIRouter(tags=["governance"])
logger = logging.getLogger("uvicorn.error")


# ─── Shared Helpers ──────────────────────────────────────────────────

_DANGEROUS_PATH_CHARS = frozenset("\0\r\n\t")
_TENANT_PATTERN = re.compile(r"^[a-z0-9_\-]+$", re.I)


def _get_lang(request: Request) -> str:
    """Extract Accept-Language from request with fallback."""
    return request.headers.get("Accept-Language", DEFAULT_LANGUAGE)


def _get_auth_manager():
    """Resolve the active auth manager singleton."""
    return api_state.auth_manager or get_auth_manager()

# ─── Project Management ──────────────────────────────────────────────


@router.get("/v1/projects/{project}/export")
async def export_project(
    project: str,
    request: Request,
    path: str | None = Query(None),
    fmt: str = Query("json", alias="format"),
    auth: AuthResult = Depends(require_permission("admin")),
    engine: CortexEngine = Depends(get_engine),
) -> dict[str, str]:
    """
    Sovereign Export: Dumps project memory to a secure JSON artifact.
    Enforces path incarceration to prevent directory traversal.
    """
    lang = _get_lang(request)

    if fmt != "json":
        raise HTTPException(status_code=400, detail=get_trans("error_json_only", lang))

    target_file = _validate_export_path(path, project, lang)

    try:
        facts = engine.search(project=project, limit=100000)
        content = export_facts(facts, fmt="json")

        def _write_export() -> Path:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(content, encoding="utf-8")
            return target_file

        out_path = await run_in_threadpool(_write_export)
        return {
            "status": "success",
            "project": project,
            "artifact": str(out_path),
            "message": get_trans("info_export_success", lang),
        }
    except (OSError, ValueError, KeyError) as exc:
        logger.error("Sovereign Export Failure: %s", exc)
        raise HTTPException(
            status_code=500, detail=get_trans("error_export_failed", lang)
        ) from None


def _validate_export_path(path: str | None, project: str, lang: str) -> Path:
    """Validate and resolve export path with traversal protection."""
    if not path:
        return Path.cwd() / f"{project}_export.json"

    if any(c in path for c in _DANGEROUS_PATH_CHARS) or ".." in path:
        raise HTTPException(status_code=400, detail=get_trans("error_invalid_path_chars", lang))

    try:
        base_dir = Path.cwd().resolve()
        target_path = Path(path).resolve()
        if not str(target_path).startswith(str(base_dir)):
            raise HTTPException(status_code=400, detail=get_trans("error_path_workspace", lang))
        return target_path
    except (ValueError, RuntimeError):
        raise HTTPException(
            status_code=400, detail=get_trans("error_invalid_input", lang)
        ) from None


@router.get("/v1/health/deep", tags=["health"])
async def deep_health_check(
    request: Request,
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict[str, Any]:
    """Deep Health Check — probes all CORTEX subsystems.

    Returns 200 if all checks pass, 503 if any subsystem is degraded.
    Designed for Kubernetes liveness/readiness probes and Enterprise monitoring.
    """
    from cortex.database.schema import SCHEMA_VERSION

    start = time.monotonic()
    checks: dict[str, dict[str, Any]] = {}
    overall_healthy = True

    conn = engine._get_conn()
    probes = _build_health_probes(conn, request, SCHEMA_VERSION)

    for name, probe in probes.items():
        try:
            status, healthy, details = probe()
        except AttributeError:
            status, healthy, details = (
                "unavailable", True, {"detail": f"{name} not in app state"}
            )
        except (OSError, RuntimeError, ValueError) as e:
            status, healthy, details = "error", False, {"detail": str(e)}
        overall_healthy = overall_healthy and healthy
        checks[name] = {"status": status, **details}

    elapsed_ms = round((time.monotonic() - start) * 1000, 1)
    result = {
        "status": "healthy" if overall_healthy else "degraded",
        "version": __version__,
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "latency_ms": elapsed_ms,
    }

    if not overall_healthy:
        from fastapi.responses import JSONResponse

        return JSONResponse(content=result, status_code=503)

    return result


def _build_health_probes(
    conn: Any, request: Request, schema_version: str
) -> dict[str, Any]:
    """Build the probe registry for deep health check."""

    def _probe_database() -> tuple[str, bool, dict[str, str]]:
        conn.execute("SELECT 1").fetchone()
        return "ok", True, {"detail": "SELECT 1 succeeded"}

    def _probe_schema() -> tuple[str, bool, dict[str, str]]:
        row = conn.execute(
            "SELECT value FROM cortex_meta WHERE key = 'schema_version'"
        ).fetchone()
        db_ver = row[0] if row else "unknown"
        if db_ver == schema_version:
            return "ok", True, {"version": db_ver}
        return "drift", False, {"expected": schema_version, "actual": db_ver}

    def _probe_ledger() -> tuple[str, bool, dict[str, Any]]:
        last_cp = conn.execute("SELECT MAX(tx_end_id) FROM merkle_roots").fetchone()
        last_tx = last_cp[0] if last_cp else 0
        pending_row = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE id > ?", (last_tx,)
        ).fetchone()
        pending = pending_row[0] if pending_row else 0
        healthy = pending < 1000
        return (
            "ok" if healthy else "warning",
            healthy,
            {"pending_uncheckpointed": pending, "last_checkpoint_tx": last_tx},
        )

    def _probe_fts() -> tuple[str, bool, dict[str, str]]:
        conn.execute("SELECT COUNT(*) FROM episodes_fts").fetchone()
        return "ok", True, {"detail": "episodes_fts accessible"}

    def _probe_pool() -> tuple[str, bool, dict[str, Any]]:
        pool = request.app.state.pool
        max_c = getattr(pool, "max_connections", 0)
        active = getattr(pool, "_active_count", 0)
        pct = (active / max_c) * 100 if max_c else 0
        return (
            "ok",
            True,
            {
                "active_connections": active,
                "max_connections": max_c,
                "utilization": f"{pct:.0f}%",
            },
        )

    return {
        "database": _probe_database,
        "schema": _probe_schema,
        "ledger": _probe_ledger,
        "search_fts": _probe_fts,
        "pool": _probe_pool,
    }


@router.get("/v1/status", response_model=StatusResponse)
async def get_system_status(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> StatusResponse:
    """Expose engine diagnostics and memory health metrics."""
    lang = _get_lang(request)
    try:
        stats = engine.stats_sync()
        return StatusResponse(
            version=__version__,
            total_facts=stats["total_facts"],
            active_facts=stats["active_facts"],
            deprecated=stats["deprecated_facts"],
            projects=stats["project_count"],
            embeddings=stats["embeddings"],
            transactions=stats["transactions"],
            db_size_mb=stats["db_size_mb"],
        )
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        logger.error("Sovereign Diagnostic Failure: %s", exc)
        raise HTTPException(
            status_code=500, detail=get_trans("error_status_unavailable", lang)
        ) from None


# ─── API Key Governance ─────────────────────────────────────────────


@router.post("/v1/admin/keys")
async def create_api_key(
    request: Request,
    name: str = Query(..., min_length=3, max_length=64),
    tenant_id: str = Query("default"),
    authorization: str | None = Header(None),
) -> dict:
    """
    Sovereign Key Provisioning.
    First key is self-provisioned (bootstrap). Subsequent keys require 'admin' permission.
    """
    lang = _get_lang(request)

    if not _TENANT_PATTERN.match(tenant_id):
        raise HTTPException(status_code=400, detail=get_trans("error_invalid_input", lang))

    manager = _get_auth_manager()
    existing_keys = await manager.list_keys()

    if existing_keys:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail=get_trans("error_auth_required", lang))

        token = authorization.split(" ", 1)[1]
        result = await manager.authenticate_async(token)

        if not result.authenticated:
            raise HTTPException(
                status_code=401, detail=get_trans("error_invalid_revoked_key", lang)
            )

        if "admin" not in result.permissions:
            detail = get_trans("error_missing_permission", lang).format(permission="admin")
            raise HTTPException(status_code=403, detail=detail)

    raw_key, api_key = await manager.create_key(
        name=name,
        tenant_id=tenant_id,
        permissions=["read", "write", "admin"],
    )

    return {
        "key": raw_key,
        "name": api_key.name,
        "prefix": api_key.key_prefix,
        "tenant_id": api_key.tenant_id,
        "message": get_trans("info_key_warning", lang),
    }


@router.get("/v1/admin/keys")
async def list_api_keys(auth: AuthResult = Depends(require_permission("admin"))) -> list[dict]:
    """Expose non-sensitive metadata for all provisioned keys."""
    manager = _get_auth_manager()
    keys = await manager.list_keys()
    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.key_prefix,
            "tenant_id": k.tenant_id,
            "permissions": k.permissions,
            "is_active": k.is_active,
            "created_at": k.created_at,
            "last_used": k.last_used,
        }
        for k in keys
    ]


# ─── Handoff & Continuity ───────────────────────────────────────────


@router.post("/v1/handoff")
async def generate_handoff_context(
    request: Request,
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """
    Manifest a session handoff artifact containing hot context and recent episodes.
    Used for transferring agentic state between platforms (macOS -> Web).
    """
    from cortex.agents.handoff import generate_handoff, save_handoff

    lang = _get_lang(request)

    try:
        body = await request.json()
    except (ValueError, TypeError):
        body = {}

    session_meta = body.get("session")
    try:
        data = await generate_handoff(engine, session_meta=session_meta)
        save_handoff(data)
        return data
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        logger.error("Handoff Generation Failure: %s", exc)
        raise HTTPException(status_code=500, detail=get_trans("error_unexpected", lang)) from None
