# [C5-REAL] Exergy-Maximized
"""
Graph Router.

Exposes entity graph endpoints for UI and external consumers.
"""

import logging
import sqlite3

from babylon60.api.deps import get_engine
from babylon60.auth import AuthResult, require_permission
from babylon60.engine import CortexEngine
from babylon60.graph import get_graph as _get_graph
from babylon60.utils.i18n import get_trans
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request

__all__ = ["get_graph", "get_graph_all"]

router = APIRouter(tags=["graph"])
logger = logging.getLogger("uvicorn.error")


@router.get("/v1/graph/{project}")
async def get_graph(
    project: str,
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """Get entity graph for a specific project."""
    lang = request.headers.get("Accept-Language", "en")
    if auth.tenant_id != "default" and project != auth.tenant_id:
        raise HTTPException(status_code=403, detail=get_trans("error_graph_forbidden", lang))

    try:
        async with engine.session() as conn:
            return await _get_graph(conn, project, limit, tenant_id=auth.tenant_id)
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error("Graph unavailable: %s", e)
        raise HTTPException(
            status_code=500, detail=get_trans("error_graph_unavailable", lang)
        ) from None


@router.get("/v1/graph")
async def get_graph_all(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """Get entity graph across all projects."""
    try:
        async with engine.session() as conn:
            return await _get_graph(conn, None, limit, tenant_id=auth.tenant_id)
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error("Graph unavailable: %s", e)
        lang = request.headers.get("Accept-Language", "en")
        raise HTTPException(
            status_code=500, detail=get_trans("error_graph_unavailable", lang)
        ) from None
