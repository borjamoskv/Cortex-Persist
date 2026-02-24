"""
CORTEX v5.1 — Admin & Governance Router.

High-privilege endpoints for project management, API key governance,
and session handoff orchestration. Enforces strict RBAC and input validation.
"""

import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from cortex import __version__
import cortex.api.state as api_state
from cortex.api.deps import get_engine
from cortex.auth import AuthResult, get_auth_manager, require_permission
from cortex.engine import CortexEngine
from cortex.utils.i18n import DEFAULT_LANGUAGE, get_trans
from cortex.types.models import StatusResponse
from cortex.utils.export import export_facts

__all__ = [
    "create_api_key",
    "export_project",
    "generate_handoff_context",
    "get_system_status",
    "list_api_keys",
]

router = APIRouter(tags=["governance"])
logger = logging.getLogger("uvicorn.error")

# ─── Project Management ──────────────────────────────────────────────


@router.get("/v1/projects/{project}/export")
async def export_project(
    project: str,
    request: Request,
    path: str | None = Query(None),
    fmt: str = Query("json", alias="format"),
    auth: AuthResult = Depends(require_permission("admin")),
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """
    Sovereign Export: Dumps project memory to a secure JSON artifact.
    Enforces path incarceration to prevent directory traversal.
    """
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)

    if fmt != "json":
        raise HTTPException(status_code=400, detail=get_trans("error_json_only", lang))

    if path:
        # Prevent traversal and control character injection
        if any(c in path for c in ("\0", "\r", "\n", "\t", "..")):
            raise HTTPException(status_code=400, detail=get_trans("error_invalid_path_chars", lang))

        try:
            base_dir = Path.cwd().resolve()
            target_path = Path(path).resolve()
            if not str(target_path).startswith(str(base_dir)):
                raise HTTPException(status_code=400, detail=get_trans("error_path_workspace", lang))
        except (ValueError, RuntimeError):
            raise HTTPException(
                status_code=400, detail=get_trans("error_invalid_input", lang)
            ) from None

    try:
        facts = engine.search(project=project, limit=100000)
        content = export_facts(facts, fmt="json")

        target_file = Path(path).resolve() if path else Path.cwd() / f"{project}_export.json"

        def _write_export():
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


@router.get("/v1/health/deep", tags=["health"])
async def deep_health_check(
    request: Request,
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """Deep Health Check — probes all CORTEX subsystems.

    Returns 200 if all checks pass, 503 if any subsystem is degraded.
    Designed for Kubernetes liveness/readiness probes and Enterprise monitoring.
    """
    import time
    from cortex.database.schema import SCHEMA_VERSION

    checks: dict[str, dict] = {}
    overall_healthy = True
    start = time.monotonic()

    # 1. Database connectivity
    try:
        conn = engine._get_conn()
        conn.execute("SELECT 1").fetchone()
        checks["database"] = {"status": "ok", "detail": "SELECT 1 succeeded"}
    except Exception as e:
        checks["database"] = {"status": "degraded", "detail": str(e)}
        overall_healthy = False

    # 2. Schema version alignment
    try:
        conn = engine._get_conn()
        row = conn.execute(
            "SELECT value FROM cortex_meta WHERE key = 'schema_version'"
        ).fetchone()
        db_version = row[0] if row else "unknown"
        if db_version == SCHEMA_VERSION:
            checks["schema"] = {
                "status": "ok",
                "version": db_version,
            }
        else:
            checks["schema"] = {
                "status": "drift",
                "expected": SCHEMA_VERSION,
                "actual": db_version,
            }
            overall_healthy = False
    except Exception as e:
        checks["schema"] = {"status": "error", "detail": str(e)}
        overall_healthy = False

    # 3. Ledger integrity (pending uncheckpointed transactions)
    try:
        conn = engine._get_conn()
        last_cp = conn.execute("SELECT MAX(tx_end_id) FROM merkle_roots").fetchone()
        last_tx = last_cp[0] or 0 if last_cp else 0
        pending_row = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE id > ?", (last_tx,)
        ).fetchone()
        pending = pending_row[0] if pending_row else 0
        checks["ledger"] = {
            "status": "ok" if pending < 1000 else "warning",
            "pending_uncheckpointed": pending,
            "last_checkpoint_tx": last_tx,
        }
        if pending >= 1000:
            overall_healthy = False
    except Exception as e:
        checks["ledger"] = {"status": "error", "detail": str(e)}

    # 4. FTS5 search index
    try:
        conn = engine._get_conn()
        conn.execute("SELECT COUNT(*) FROM episodes_fts").fetchone()
        checks["search_fts"] = {"status": "ok", "detail": "episodes_fts accessible"}
    except Exception as e:
        checks["search_fts"] = {"status": "degraded", "detail": str(e)}

    # 5. Pool status (if async pool is available)
    try:
        pool = request.app.state.pool
        checks["pool"] = {
            "status": "ok",
            "active_connections": pool._active_count,
            "max_connections": pool.max_connections,
            "utilization": f"{(pool._active_count / pool.max_connections) * 100:.0f}%",
        }
    except Exception:
        checks["pool"] = {"status": "unavailable", "detail": "pool not in app state"}

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


@router.get("/v1/status", response_model=StatusResponse)
async def get_system_status(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> StatusResponse:
    """Expose engine diagnostics and memory health metrics."""
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
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
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)

    # Sanitize tenant_id (Alphanumeric + safe separators)
    if not re.match(r"^[a-z0-9_\-]+$", tenant_id, re.I):
        raise HTTPException(status_code=400, detail=get_trans("error_invalid_input", lang))

    manager = api_state.auth_manager or get_auth_manager()
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
    manager = api_state.auth_manager or get_auth_manager()
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

    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)

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
