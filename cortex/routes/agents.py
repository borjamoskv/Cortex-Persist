# [C5-REAL] Exergy-Maximized
"""
Agents Router — Registro con puente determinista al SwarmRegistry.
"""

import logging
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex.types.models import AgentRegisterRequest, AgentResponse
from cortex.types.swarm import AgentRegisterRequestV2
from cortex.utils.i18n import get_trans

__all__ = ["get_agent", "list_agents", "register_agent", "register_agent_v2"]

router = APIRouter(tags=["agents"])
logger = logging.getLogger("uvicorn.error")


# ── helpers ──────────────────────────────────────────────────────────


def _get_swarm_registry(request: Request):
    """
    Recupera swarm_registry desde app.state.
    Falla rápido con 503 si el lifecycle no lo montó todavía.
    """
    registry = getattr(request.app.state, "swarm_registry", None)
    if registry is None:
        raise HTTPException(
            status_code=503,
            detail="swarm_registry not initialized — check lifecycle startup order",
        )
    return registry


# ── V1 (backward-compat, sin capabilities) ───────────────────────────


@router.post("/v1/agents", response_model=AgentResponse)
async def register_agent(
    req: AgentRegisterRequest,
    request: Request,
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> AgentResponse:
    """Registro legado (V1). Sin capabilities → no alimenta swarm kinds."""
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
                status_code=500,
                detail=get_trans("error_agent_registration_failed", lang),
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
        logger.exception("Agent registration failed (v1)")
        lang = request.headers.get("Accept-Language", "en")
        raise HTTPException(
            status_code=500, detail=get_trans("error_agent_internal", lang)
        ) from None


# ── V2 (capabilities → kinds → swarm_registry) ───────────────────────


@router.post("/v2/agents", response_model=AgentResponse)
async def register_agent_v2(
    req: AgentRegisterRequestV2,
    request: Request,
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> AgentResponse:
    """
    Registro V2 con routing determinista.

    Flujo:
      1. Persiste agente en engine (memoria + DB).
      2. Construye meta con capabilities y kinds.
      3. Registra en swarm_registry → permite resolve("audit") etc.
    """
    lang = request.headers.get("Accept-Language", "en")

    # ── 1. Persistencia en engine ────────────────────────────────────
    try:
        agent_id = await engine.register_agent(
            name=req.name,
            agent_type=req.agent_type,
            public_key=req.public_key or "",
            tenant_id=auth.tenant_id,
        )
        agent = await engine.get_agent(agent_id, tenant_id=auth.tenant_id)
        if not agent:
            raise HTTPException(
                status_code=500,
                detail=get_trans("error_agent_registration_failed", lang),
            )
    except HTTPException:
        raise
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Agent registration failed (v2) — engine layer")
        raise HTTPException(
            status_code=500, detail=get_trans("error_agent_internal", lang)
        ) from None

    # ── 2. Construir meta (sin romper AgentResponse) ─────────────────
    meta: dict = {
        "capabilities": req.capabilities,   # lista completa (soft + hard)
        "kinds": req.kinds,                  # subconjunto de routing duro
        "tags": req.tags,                    # semántica blanda
        "priority": req.priority,
        "tenant_id": auth.tenant_id,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }

    # ── 3. Inyección en swarm_registry ───────────────────────────────
    registry = _get_swarm_registry(request)
    try:
        from cortex.swarm.runtime import AgentCapability

        meta["agent_id"] = agent_id  # Aseguramos el cruce con BD
        
        registry.register(
            AgentCapability(
                name=req.name,
                kinds=req.kinds,  # type: ignore
                tags=req.tags or [],
                priority=req.priority,
                meta=meta,
            )
        )
        logger.info(
            "Agent %s registered in swarm_registry with kinds=%s priority=%d",
            agent_id,
            req.kinds,
            req.priority,
        )
    except Exception:
        # El agente ya está en DB; loguear pero no revertir el registro engine.
        # El operador puede hacer re-register sin consecuencias.
        logger.exception(
            "swarm_registry.register() failed for agent %s — "
            "agent persisted in engine but NOT routable via swarm",
            agent_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Agent persisted but swarm registration failed. Retry register.",
        )

    # ── 4. Respuesta — AgentResponse sin cambios de modelo ───────────
    return AgentResponse(
        agent_id=agent["id"],
        name=agent["name"],
        agent_type=agent["agent_type"],
        reputation_score=agent["reputation_score"],
        created_at=agent["created_at"],
    )


# ── READ endpoints (sin cambios) ─────────────────────────────────────


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
        raise HTTPException(
            status_code=404, detail=get_trans("error_agent_not_found", lang)
        )
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
