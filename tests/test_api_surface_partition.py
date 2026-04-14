from __future__ import annotations

from fastapi.routing import APIRoute

from cortex.routes import api_router_core, build_api_router


def _route_paths(router) -> set[str]:
    return {
        route.path
        for route in router.routes
        if isinstance(route, APIRoute)
    }


def test_core_router_exposes_only_default_product_surface() -> None:
    paths = _route_paths(api_router_core)

    assert "/v1/facts" in paths
    assert "/v1/search" in paths
    assert "/v1/ledger/status" in paths
    assert "/v1/trust/compliance" in paths
    assert "/v1/swarm/status" not in paths
    assert "/v1/agents" not in paths
    assert "/v1/context" not in paths
    assert "/v1/runtime/health" not in paths
    assert "/v1/events/stream" not in paths


def test_opt_in_router_adds_experimental_paths_without_dropping_core() -> None:
    paths = _route_paths(build_api_router(include_experimental=True))

    assert "/v1/facts" in paths
    assert "/v1/search" in paths
    assert "/v1/swarm/status" in paths
    assert "/v1/agents" in paths
    assert "/v1/context/infer" in paths
    assert "/v1/runtime/health" in paths
    assert "/v1/events/stream" in paths
