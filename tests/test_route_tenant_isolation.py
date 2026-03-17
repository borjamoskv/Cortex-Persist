from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine, get_engine
from cortex.auth.models import AuthResult
from cortex.routes import agents as agents_router
from cortex.routes import graph as graph_router


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def test_graph_all_scopes_calls_to_authenticated_tenant(monkeypatch) -> None:
    observed: dict[str, object] = {}

    class FakeEngine:
        async def get_conn(self) -> object:
            return object()

    async def fake_get_graph(
        conn: object,
        project: str | None = None,
        limit: int = 50,
        tenant_id: str = "default",
    ) -> dict[str, object]:
        observed.update({"project": project, "limit": limit, "tenant_id": tenant_id})
        return observed.copy()

    monkeypatch.setattr(graph_router, "_get_graph", fake_get_graph)

    app = FastAPI()
    app.include_router(graph_router.router)
    auth_dep = _dependency_for(
        "/v1/graph", "GET", _route_by_path(graph_router.router, "/v1/graph", "GET")
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-graph",
        permissions=["read"],
    )
    app.dependency_overrides[get_engine] = lambda: FakeEngine()

    with TestClient(app) as client:
        response = client.get("/v1/graph?limit=25")

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-graph"
    assert observed == {"project": None, "limit": 25, "tenant_id": "tenant-graph"}


def test_get_agent_scopes_lookup_to_authenticated_tenant() -> None:
    class FakeAsyncEngine:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str | None]] = []

        async def get_agent(self, agent_id: str, tenant_id: str | None = None) -> dict | None:
            self.calls.append((agent_id, tenant_id))
            if agent_id == "agent-1" and tenant_id == "tenant-agents":
                return {
                    "id": "agent-1",
                    "name": "agent-one",
                    "agent_type": "ai",
                    "reputation_score": 1.0,
                    "created_at": "2026-01-01T00:00:00Z",
                }
            return None

    fake_engine = FakeAsyncEngine()

    app = FastAPI()
    app.include_router(agents_router.router)
    auth_dep = _dependency_for(
        "/v1/agents/{agent_id}",
        "GET",
        _route_by_path(agents_router.router, "/v1/agents/{agent_id}", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-agents",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/agents/agent-1")

    assert response.status_code == 200
    assert response.json()["agent_id"] == "agent-1"
    assert fake_engine.calls == [("agent-1", "tenant-agents")]
