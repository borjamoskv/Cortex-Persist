from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter

__all__ = ["api_router"]

_ROUTE_MODULES = {
    "admin",
    "agents",
    "ask",
    "context",
    "daemon",
    "dashboard",
    "events",
    "facts",
    "gate",
    "graph",
    "health",
    "ledger",
    "mejoralo",
    "missions",
    "onboarding",
    "oracle",
    "runtime",
    "search",
    "swarm",
    "telemetry",
    "timing",
    "tips",
    "topology_ws",
    "translate",
    "trust",
    "usage",
}

_API_ROUTE_SPECS: tuple[tuple[str, str], ...] = (
    ("events", "events_router"),
    ("facts", "router"),
    ("search", "router"),
    ("ask", "router"),
    ("admin", "router"),
    ("timing", "router"),
    ("translate", "router"),
    ("oracle", "router"),
    ("daemon", "router"),
    ("dashboard", "router"),
    ("agents", "router"),
    ("graph", "router"),
    ("ledger", "router"),
    ("missions", "router"),
    ("mejoralo", "router"),
    ("gate", "router"),
    ("context", "router"),
    ("tips", "router"),
    ("swarm", "router"),
    ("telemetry", "router"),
    ("topology_ws", "router"),
    ("usage", "router"),
    ("runtime", "router"),
    ("onboarding", "router"),
    ("health", "router"),
    ("trust", "router"),
)


def _load_route_module(name: str):
    module = importlib.import_module(f".{name}", __name__)
    globals()[name] = module
    return module


def _build_api_router() -> APIRouter:
    from fastapi import APIRouter

    router = APIRouter()
    for module_name, router_attr in _API_ROUTE_SPECS:
        module = _load_route_module(module_name)
        router.include_router(getattr(module, router_attr))
    return router


def __getattr__(name: str):
    if name == "api_router":
        router = _build_api_router()
        globals()[name] = router
        return router
    if name in _ROUTE_MODULES:
        return _load_route_module(name)
    raise AttributeError(f"module 'cortex.routes' has no attribute {name!r}")
