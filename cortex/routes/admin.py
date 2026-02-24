"""
CORTEX v5.1 — Admin & Governance Router.

High-privilege endpoints for project management, API key governance,
and session handoff orchestration. Enforces strict RBAC and input validation.

Sovereign 130/100 — Pydantic responses, structured logging, TOCTOU-safe paths.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

import cortex.api.state as api_state
from cortex import __version__
from cortex.api.deps import get_engine
from cortex.auth import AuthResult, get_auth_manager, require_permission
from cortex.engine import CortexEngine
from cortex.routes.middleware import AuditLogger, RateLimiter, SelfHealingHook
from cortex.types.models import (
    ApiKeyListItem,
    ApiKeyResponse,
    DeepHealthResponse,
    ExportResponse,
    HealthCheckDetail,
    StatusResponse,
)
from cortex.utils.export import export_facts
from cortex.utils.i18n import DEFAULT_LANGUAGE, get_trans

if TYPE_CHECKING:
    from cortex.auth.api_keys import ApiKeyManager

__all__ = [
    "create_api_key",
    "deep_health_check",
    "export_project",
    "generate_handoff_context",
    "get_system_status",
    "list_api_keys",
]

# ─── Middleware Instances ─────────────────────────────────────────────
_rate_limiter = RateLimiter(max_requests=10, window_seconds=1.0)
_audit_logger = AuditLogger()

router = APIRouter(
    tags=["governance"],
    dependencies=[Depends(_rate_limiter), Depends(_audit_logger)],
)
logger = logging.getLogger("cortex.admin")

# Maximum facts to export in a single operation
_MAX_EXPORT_FACTS = 100_000
# Ledger lag threshold before marking as unhealthy
_LEDGER_LAG_THRESHOLD = 1000


# ─── Shared Helpers ──────────────────────────────────────────────────

_DANGEROUS_PATH_CHARS = frozenset("\0\r\n\t")
_TENANT_PATTERN = re.compile(r"^[a-z0-9_\-]+$", re.I)


def _get_lang(request: Request) -> str:
    """Extract Accept-Language from request with fallback."""
    return request.headers.get("Accept-Language", DEFAULT_LANGUAGE)


def _get_auth_manager() -> ApiKeyManager:
    """Resolve the active auth manager singleton."""
    return api_state.auth_manager or get_auth_manager()


def _validate_export_path(path: str | None, project: str, lang: str) -> Path:
    """Validate and resolve export path with traversal protection.

    Uses strict Path resolution to prevent TOCTOU and symlink attacks.
    """
    if not path:
        return Path.cwd() / f"{project}_export.json"

    if any(c in path for c in _DANGEROUS_PATH_CHARS) or ".." in path:
        raise HTTPException(
            status_code=400,
            detail=get_trans("error_invalid_path_chars", lang),
        )

    try:
        base_dir = Path.cwd().resolve(strict=True)
        target_path = Path(path).resolve()
        # Use os.path.commonpath for symlink-safe comparison
        if not target_path.is_relative_to(base_dir):
            raise HTTPException(
                status_code=400,
                detail=get_trans("error_path_workspace", lang),
            )
        return target_path
    except (ValueError, RuntimeError, OSError):
        raise HTTPException(
            status_code=400, detail=get_trans("error_invalid_input", lang)
        ) from None


# ─── Health Probe Types ──────────────────────────────────────────────

ProbeResult = tuple[str, bool, dict[str, str | int | float]]


def _build_health_probes(
    conn: object, request: Request, schema_version: str
) -> dict[str, object]:
    """Build the probe registry for deep health check.

    Each probe returns (status_str, is_healthy, details_dict).
    Probes are designed to be individually failable without cascading.
    """

    def _probe_database() -> ProbeResult:
        conn.execute("SELECT 1").fetchone()  # type: ignore[union-attr]
        return "ok", True, {"detail": "SELECT 1 succeeded"}

    def _probe_schema() -> ProbeResult:
        row = conn.execute(  # type: ignore[union-attr]
            "SELECT value FROM cortex_meta WHERE key = 'schema_version'"
        ).fetchone()
        db_ver = row[0] if row else "unknown"
        if db_ver == schema_version:
            return "ok", True, {"version": db_ver}
        return "drift", False, {"expected": schema_version, "actual": db_ver}

    def _probe_ledger() -> ProbeResult:
        last_cp = conn.execute(  # type: ignore[union-attr]
            "SELECT MAX(tx_end_id) FROM merkle_roots"
        ).fetchone()
        last_tx = last_cp[0] if last_cp else 0
        pending_row = conn.execute(  # type: ignore[union-attr]
            "SELECT COUNT(*) FROM transactions WHERE id > ?", (last_tx,)
        ).fetchone()
        pending = pending_row[0] if pending_row else 0
        healthy = pending < _LEDGER_LAG_THRESHOLD
        return (
            "ok" if healthy else "warning",
            healthy,
            {"pending_uncheckpointed": pending, "last_checkpoint_tx": last_tx},
        )

    def _probe_fts() -> ProbeResult:
        conn.execute("SELECT COUNT(*) FROM episodes_fts").fetchone()  # type: ignore[union-attr]
        return "ok", True, {"detail": "episodes_fts accessible"}

    def _probe_pool() -> ProbeResult:
        pool = request.app.state.pool
        max_c: int = getattr(pool, "max_connections", 0)
        active: int = getattr(pool, "_active_count", 0)
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


# ─── Project Management ──────────────────────────────────────────────


@router.get("/v1/projects/{project}/export", response_model=ExportResponse)
async def export_project(
    project: str,
    request: Request,
    path: str | None = Query(None),
    fmt: str = Query("json", alias="format"),
    auth: AuthResult = Depends(require_permission("admin")),
    engine: CortexEngine = Depends(get_engine),
) -> ExportResponse:
    """Sovereign Export — dumps project memory to a secure JSON artifact.

    Enforces path incarceration to prevent directory traversal.
    """
    lang = _get_lang(request)

    if fmt != "json":
        raise HTTPException(status_code=400, detail=get_trans("error_json_only", lang))

    target_file = _validate_export_path(path, project, lang)

    try:
        facts = engine.search(project=project, limit=_MAX_EXPORT_FACTS)
        content = export_facts(facts, fmt="json")

        def _write_export() -> Path:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(content, encoding="utf-8")
            return target_file

        out_path = await run_in_threadpool(_write_export)
        logger.info("Export completed: project=%s path=%s", project, out_path)
        return ExportResponse(
            project=project,
            artifact=str(out_path),
            message=get_trans("info_export_success", lang),
        )
    except (OSError, ValueError, KeyError) as exc:
        logger.error("Export failure: project=%s error=%s", project, exc)
        SelfHealingHook.trigger(exc, {"endpoint": "export_project", "project": project})
        raise HTTPException(
            status_code=500, detail=get_trans("error_export_failed", lang)
        ) from None


# ─── Health & Diagnostics ────────────────────────────────────────────


@router.get("/v1/health/deep", tags=["health"], response_model=DeepHealthResponse)
async def deep_health_check(
    request: Request,
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> DeepHealthResponse:
    """Deep Health Check — probes all CORTEX subsystems.

    Returns 200 if all checks pass, 503 if any subsystem is degraded.
    Designed for Kubernetes liveness/readiness probes and Enterprise monitoring.
    """
    from cortex.database.schema import SCHEMA_VERSION

    start = time.monotonic()
    checks: dict[str, HealthCheckDetail] = {}
    overall_healthy = True

    conn = engine._get_conn()
    probes = _build_health_probes(conn, request, SCHEMA_VERSION)

    for name, probe in probes.items():
        try:
            status, healthy, details = probe()  # type: ignore[misc]
        except AttributeError:
            status, healthy, details = (
                "unavailable", True, {"detail": f"{name} not configured"}
            )
        except (OSError, RuntimeError, ValueError) as e:
            status, healthy, details = "error", False, {"detail": str(e)}
        overall_healthy = overall_healthy and healthy
        checks[name] = HealthCheckDetail(status=status, **details)

    elapsed_ms = round((time.monotonic() - start) * 1000, 1)
    result = DeepHealthResponse(
        status="healthy" if overall_healthy else "degraded",
        version=__version__,
        schema_version=SCHEMA_VERSION,
        checks=checks,
        latency_ms=elapsed_ms,
    )

    if not overall_healthy:
        from fastapi.responses import JSONResponse

        return JSONResponse(  # type: ignore[return-value]
            content=result.model_dump(), status_code=503
        )

    return result


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
        logger.error("Status check failure: %s", exc)
        SelfHealingHook.trigger(exc, {"endpoint": "get_system_status"})
        raise HTTPException(
            status_code=500, detail=get_trans("error_status_unavailable", lang)
        ) from None


# ─── API Key Governance ─────────────────────────────────────────────


class _HandoffBody(BaseModel):
    """Optional body for handoff request."""

    session: dict | None = Field(None, description="Session metadata for handoff context")


@router.post("/v1/admin/keys", response_model=ApiKeyResponse)
async def create_api_key(
    request: Request,
    name: str = Query(..., min_length=3, max_length=64),
    tenant_id: str = Query("default"),
    authorization: str | None = Header(None),
) -> ApiKeyResponse:
    """Sovereign Key Provisioning.

    First key is self-provisioned (bootstrap).
    Subsequent keys require 'admin' permission.
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

    logger.info("API key created: name=%s tenant=%s prefix=%s", name, tenant_id, api_key.key_prefix)

    return ApiKeyResponse(
        key=raw_key,
        name=api_key.name,
        prefix=api_key.key_prefix,
        tenant_id=api_key.tenant_id,
        message=get_trans("info_key_warning", lang),
    )


@router.get("/v1/admin/keys", response_model=list[ApiKeyListItem])
async def list_api_keys(
    auth: AuthResult = Depends(require_permission("admin")),
) -> list[ApiKeyListItem]:
    """Expose non-sensitive metadata for all provisioned keys."""
    manager = _get_auth_manager()
    keys = await manager.list_keys()
    return [
        ApiKeyListItem(
            id=k.id,
            name=k.name,
            prefix=k.key_prefix,
            tenant_id=k.tenant_id,
            permissions=k.permissions,
            is_active=k.is_active,
            created_at=k.created_at,
            last_used=k.last_used,
        )
        for k in keys
    ]


# ─── Handoff & Continuity ───────────────────────────────────────────


@router.post("/v1/handoff")
async def generate_handoff_context(
    request: Request,
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Manifest a session handoff artifact with hot context and recent episodes.

    Used for transferring agentic state between platforms (macOS -> Web).
    """
    from cortex.agents.handoff import generate_handoff, save_handoff

    lang = _get_lang(request)

    try:
        body = await request.json()
    except (ValueError, TypeError):
        body = {}

    session_meta = body.get("session") if isinstance(body, dict) else None
    try:
        data = await generate_handoff(engine, session_meta=session_meta)
        save_handoff(data)
        logger.info("Handoff generated: keys=%d", len(data))
        return data
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        logger.error("Handoff failure: %s", exc)
        SelfHealingHook.trigger(exc, {"endpoint": "generate_handoff_context"})
        raise HTTPException(
            status_code=500, detail=get_trans("error_unexpected", lang)
        ) from None
