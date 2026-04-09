from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.routes import agents as agents_router
from cortex.routes import facts as facts_router
from cortex.routes import memories as memories_router


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class _FakeRouteEngine:
    def __init__(self) -> None:
        self.recall_calls: list[dict[str, object]] = []
        self.history_calls: list[dict[str, object]] = []
        self.active_fact_calls: list[dict[str, object]] = []
        self.agent_calls: list[dict[str, object]] = []
        self.vote_calls: list[dict[str, object]] = []
        self.fact_exists = True

    async def recall(
        self,
        project: str,
        tenant_id: str = "default",
        limit: int | None = None,
        offset: int = 0,
        **_: object,
    ) -> list[dict]:
        self.recall_calls.append(
            {
                "project": project,
                "tenant_id": tenant_id,
                "limit": limit,
                "offset": offset,
            }
        )
        return []

    async def history(
        self,
        project: str,
        tenant_id: str = "default",
        **_: object,
    ) -> list[dict]:
        self.history_calls.append(
            {
                "project": project,
                "tenant_id": tenant_id,
            }
        )
        return []

    async def list_agents(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        self.agent_calls.append(
            {
                "tenant_id": tenant_id,
                "limit": limit,
                "offset": offset,
            }
        )
        return []

    async def get_all_active_facts(self, tenant_id: str) -> list[dict]:
        self.active_fact_calls.append({"tenant_id": tenant_id})
        return []

    async def get_votes(self, fact_id: int, tenant_id: str = "default") -> list[dict]:
        self.vote_calls.append({"fact_id": fact_id, "tenant_id": tenant_id})
        return []

    async def get_fact(self, fact_id: int, tenant_id: str = "default") -> dict:
        if not self.fact_exists:
            return None
        return {"id": fact_id, "tenant_id": tenant_id}


def test_list_project_facts_forwards_offset_and_limit() -> None:
    fake_engine = _FakeRouteEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/projects/{project}/facts",
        "GET",
        _route_by_path(facts_router.router, "/v1/projects/{project}/facts", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/projects/alpha/facts?limit=25&offset=10")

    assert response.status_code == 200
    assert response.json() == []
    assert fake_engine.recall_calls == [
        {
            "project": "alpha",
            "tenant_id": "tenant-facts",
            "limit": 25,
            "offset": 10,
        }
    ]


def test_list_project_facts_can_include_deprecated_history() -> None:
    fake_engine = _FakeRouteEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/projects/{project}/facts",
        "GET",
        _route_by_path(facts_router.router, "/v1/projects/{project}/facts", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/projects/alpha/facts?include_deprecated=true")

    assert response.status_code == 200
    assert response.json() == []
    assert fake_engine.history_calls == [{"project": "alpha", "tenant_id": "tenant-facts"}]


def test_list_all_facts_forwards_offset_and_blank_project() -> None:
    fake_engine = _FakeRouteEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts",
        "GET",
        _route_by_path(facts_router.router, "/v1/facts", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/facts?limit=15&offset=5")

    assert response.status_code == 200
    assert response.json() == []
    assert fake_engine.active_fact_calls == [{"tenant_id": "tenant-facts"}]


def test_list_memories_forwards_offset_and_limit() -> None:
    fake_engine = _FakeRouteEngine()

    app = FastAPI()
    app.include_router(memories_router.router)
    auth_dep = _dependency_for(
        "/v1/memories",
        "GET",
        _route_by_path(memories_router.router, "/v1/memories", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-memories",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/memories?project=alpha&limit=30&offset=20")

    assert response.status_code == 200
    assert response.json() == []
    assert fake_engine.recall_calls == [
        {
            "project": "alpha",
            "tenant_id": "tenant-memories",
            "limit": 30,
            "offset": 20,
        }
    ]


def test_list_agents_forwards_offset_and_limit() -> None:
    fake_engine = _FakeRouteEngine()

    app = FastAPI()
    app.include_router(agents_router.router)
    auth_dep = _dependency_for(
        "/v1/agents",
        "GET",
        _route_by_path(agents_router.router, "/v1/agents", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-agents",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/agents?limit=40&offset=12")

    assert response.status_code == 200
    assert response.json() == []
    assert fake_engine.agent_calls == [
        {
            "tenant_id": "tenant-agents",
            "limit": 40,
            "offset": 12,
        }
    ]


def test_list_votes_forwards_tenant_scope() -> None:
    fake_engine = _FakeRouteEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}/votes",
        "GET",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}/votes", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-votes",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/facts/42/votes")

    assert response.status_code == 200
    assert response.json() == []
    assert fake_engine.vote_calls == [{"fact_id": 42, "tenant_id": "tenant-votes"}]


def test_list_votes_does_not_query_votes_when_fact_missing() -> None:
    fake_engine = _FakeRouteEngine()
    fake_engine.fact_exists = False

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}/votes",
        "GET",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}/votes", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-votes",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get("/v1/facts/42/votes")

    assert response.status_code == 404
    assert fake_engine.vote_calls == []
