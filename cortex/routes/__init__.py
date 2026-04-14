from fastapi import APIRouter

from cortex import config

# Temporarily removed due to P0 gateway module topological collapse
# from cortex.gateway.adapters import (
#     rest_router as gateway_rest_router,
# )
# from cortex.gateway.adapters import (
#     telegram_router as gateway_telegram_router,
# )
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
from . import demo as demo_router

__all__ = [
    "api_router",
    "api_router_core",
    "api_router_experimental",
    "build_api_router",
]

_CORE_ROUTE_GROUPS = (
    facts_router.router,
    search_router.router,
    admin_router.router,
    ledger_router.router,
    health_index_router.router,
    trust_router.router,
)

_EXPERIMENTAL_ROUTE_GROUPS = (
    events_router.events_router,
    ask_router.router,
    timing_router.router,
    translate_router.router,
    oracle_router.router,
    daemon_router.router,
    dashboard_router.router,
    agents_router.router,
    graph_router.router,
    missions_router.router,
    mejoralo_router.router,
    gate_router.router,
    context_router.router,
    tips_router.router,
    swarm_router.router,
    telemetry_router.router,
    topology_ws_router.router,
    usage_router.router,
    runtime_router.router,
    onboarding_router.router,
    demo_router.router,
)


def _include_route_groups(target: APIRouter, groups: tuple[APIRouter, ...]) -> APIRouter:
    for group in groups:
        target.include_router(group)
    return target


def build_api_router(include_experimental: bool = False) -> APIRouter:
    """Build the public API surface for the requested exposure tier."""
    router = APIRouter()
    _include_route_groups(router, _CORE_ROUTE_GROUPS)
    if include_experimental:
        _include_route_groups(router, _EXPERIMENTAL_ROUTE_GROUPS)
    return router


api_router_core = _include_route_groups(APIRouter(), _CORE_ROUTE_GROUPS)
api_router_experimental = _include_route_groups(APIRouter(), _EXPERIMENTAL_ROUTE_GROUPS)
api_router = build_api_router(include_experimental=config.ENABLE_EXPERIMENTAL_API)

# Gateway endpoints (SovereignLLM Entry Points)
# api_router.include_router(gateway_rest_router)
# api_router.include_router(gateway_telegram_router)
