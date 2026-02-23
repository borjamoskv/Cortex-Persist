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

from cortex import __version__, api_state
from cortex.api_deps import get_engine
from cortex.auth import AuthResult, get_auth_manager, require_permission
from cortex.engine import CortexEngine
from cortex.i18n import DEFAULT_LANGUAGE, get_trans
from cortex.models import StatusResponse
from cortex.sync import export_to_json

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
        # run_in_threadpool used because export_to_json performs synchronous I/O
        out_path = await run_in_threadpool(export_to_json, engine, project, path)
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


@router.get("/v1/status", response_model=StatusResponse)
async def get_system_status(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> StatusResponse:
    """Expose engine diagnostics and memory health metrics."""
    lang = request.headers.get("Accept-Language", DEFAULT_LANGUAGE)
    try:
        stats = engine.stats()
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
        result = manager.authenticate(token)

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
    keys = manager.list_keys()
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
    from cortex.handoff import generate_handoff, save_handoff

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
