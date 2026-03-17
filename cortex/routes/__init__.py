from fastapi import APIRouter

from cortex.gateway.adapters import (
    rest_router as gateway_rest_router,
)
from cortex.gateway.adapters import (
    telegram_router as gateway_telegram_router,
)

from . import admin as admin_router
from . import agents as agents_router
from . import ask as ask_router
from . import context as context_router
from . import daemon as daemon_router
from . import dashboard as dashboard_router
from . import events as events_router
from . import facts as facts_router
from . import gate as gate_router
from . import graph as graph_router
from . import health as health_index_router
from . import ledger as ledger_router
from . import mejoralo as mejoralo_router
from . import missions as missions_router
from . import onboarding as onboarding_router
from . import oracle as oracle_router
from . import runtime as runtime_router
from . import search as search_router
from . import swarm as swarm_router
from . import telemetry as telemetry_router
from . import timing as timing_router
from . import tips as tips_router
from . import topology_ws as topology_ws_router
from . import translate as translate_router
from . import trust as trust_router
from . import usage as usage_router

__all__ = ["api_router"]

api_router = APIRouter()

# Register all internal routers to the unified `api_router`
api_router.include_router(events_router.events_router)
api_router.include_router(facts_router.router)
api_router.include_router(search_router.router)
api_router.include_router(ask_router.router)
api_router.include_router(admin_router.router)
api_router.include_router(timing_router.router)
api_router.include_router(translate_router.router)
api_router.include_router(oracle_router.router)
api_router.include_router(daemon_router.router)
api_router.include_router(dashboard_router.router)
api_router.include_router(agents_router.router)
api_router.include_router(graph_router.router)
api_router.include_router(ledger_router.router)
api_router.include_router(missions_router.router)
api_router.include_router(mejoralo_router.router)
api_router.include_router(gate_router.router)
api_router.include_router(context_router.router)
api_router.include_router(tips_router.router)
api_router.include_router(swarm_router.router)
api_router.include_router(telemetry_router.router)
api_router.include_router(topology_ws_router.router)
api_router.include_router(usage_router.router)
api_router.include_router(runtime_router.router)
api_router.include_router(onboarding_router.router)
api_router.include_router(health_index_router.router)
api_router.include_router(trust_router.router)

# Gateway endpoints (SovereignLLM Entry Points)
api_router.include_router(gateway_rest_router)
api_router.include_router(gateway_telegram_router)
