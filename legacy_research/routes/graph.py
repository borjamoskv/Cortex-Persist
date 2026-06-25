# [C5-REAL] Exergy-Maximized
"""
Graph Router.

Exposes entity graph endpoints for UI and external consumers.
"""

import logging
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request

from cortex.api.deps import get_engine
from legacy_research.auth import AuthResult, require_permission
from cortex.engine import CortexEngine
from legacy_research.graph import get_graph as _get_graph
from legacy_research.utils.i18n import get_trans

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
