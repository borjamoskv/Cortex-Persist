# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter

__all__ = ["api_router"]  # pyright: ignore[reportUnsupportedDunderAll]

_ROUTE_MODULES_ALL = {
    "admin",
    "agents",
    "ask",
    "benchmark",
    "daemon",
    "dashboard",
    "events",
    "facts",
    "gate",
    "graph",
    "ledger",
    "mejoralo",
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
    "taas",
    "ultramap",
}

_API_ROUTE_SPECS_ALL: tuple[tuple[str, str], ...] = (
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
    ("mejoralo", "router"),
    ("gate", "router"),
    ("tips", "router"),
    ("swarm", "router"),
    ("telemetry", "router"),
    ("topology_ws", "router"),
    ("runtime", "router"),
    ("trust", "router"),
    ("taas", "router"),
    ("benchmark", "router"),
    ("ultramap", "router"),
)

from babylon60.core import config

_DANGEROUS_CLOUD_ROUTES = {
    "admin",
    "daemon",
    "dashboard",
    "ledger",
    "swarm",
    "telemetry",
    "runtime",
    "taas",
    "benchmark",
    "gate",
    "mejoralo",
}

if config.DEPLOY_MODE == "cloud":
    _API_ROUTE_SPECS = tuple(r for r in _API_ROUTE_SPECS_ALL if r[0] not in _DANGEROUS_CLOUD_ROUTES)
    _ROUTE_MODULES = {m for m in _ROUTE_MODULES_ALL if m not in _DANGEROUS_CLOUD_ROUTES}
else:
    _API_ROUTE_SPECS = _API_ROUTE_SPECS_ALL
    _ROUTE_MODULES = _ROUTE_MODULES_ALL


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
