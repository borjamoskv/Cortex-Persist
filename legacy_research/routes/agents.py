# [C5-REAL] Exergy-Maximized
"""
Agents Router (Reputation Management).
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

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

from legacy_research.api.deps import get_async_engine
from legacy_research.auth import AuthResult, require_permission
from legacy_research.engine import CortexEngine as AsyncCortexEngine
from legacy_research.types.models import AgentRegisterRequest, AgentResponse
from legacy_research.utils.i18n import get_trans

__all__ = ["get_agent", "list_agents", "register_agent"]

router = APIRouter(tags=["agents"])
logger = logging.getLogger("uvicorn.error")


@router.post("/v1/agents", response_model=AgentResponse)
async def register_agent(
    req: AgentRegisterRequest,
    request: Request,
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> AgentResponse:
    """Register a new agent for Reputation-Weighted Consensus (Requires Admin)."""
    try:
        agent_id = await engine.register_agent(
            name=req.name,
            agent_type=req.agent_type,
            public_key=req.public_key or "",
            tenant_id=auth.tenant_id,
        )

        agent = await engine.get_agent(agent_id, tenant_id=auth.tenant_id)
        if not agent:
            lang = request.headers.get("Accept-Language", "en")
            raise HTTPException(
                status_code=500, detail=get_trans("error_agent_registration_failed", lang)
            )

        return AgentResponse(
            agent_id=agent["id"],
            name=agent["name"],
            agent_type=agent["agent_type"],
            reputation_score=agent["reputation_score"],
            created_at=agent["created_at"],
        )
    except HTTPException:
        raise
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Agent registration failed")
        lang = request.headers.get("Accept-Language", "en")
        raise HTTPException(
            status_code=500, detail=get_trans("error_agent_internal", lang)
        ) from None


@router.get("/v1/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> AgentResponse:
    """Get agent details and current reputation."""
    agent = await engine.get_agent(agent_id, tenant_id=auth.tenant_id)
    if not agent:
        lang = request.headers.get("Accept-Language", "en")
        raise HTTPException(status_code=404, detail=get_trans("error_agent_not_found", lang))

    return AgentResponse(
        agent_id=agent["id"],
        name=agent["name"],
        agent_type=agent["agent_type"],
        reputation_score=agent["reputation_score"],
        created_at=agent["created_at"],
    )


@router.get("/v1/agents", response_model=list[AgentResponse])
async def list_agents(
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[AgentResponse]:
    """List all agents for the current tenant."""
    agents = await engine.list_agents(auth.tenant_id)
    return [
        AgentResponse(
            agent_id=a["id"],
            name=a["name"],
            agent_type=a["agent_type"],
            reputation_score=a["reputation_score"],
            created_at=a["created_at"],
        )
        for a in agents
    ]
