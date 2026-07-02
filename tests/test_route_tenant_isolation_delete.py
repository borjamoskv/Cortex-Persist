# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from babylon60.api.deps import get_async_engine
from babylon60.auth.models import AuthResult
from babylon60.routes import facts as facts_router
from babylon60.routes import memories as memories_router


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class _FakeAsyncEngine:
    def __init__(self) -> None:
        self.deprecate_calls: list[tuple[int, str | None, str]] = []
        self.get_fact_calls: list[tuple[int, str]] = []

    async def get_fact(self, fact_id: int, tenant_id: str = "default"):
        self.get_fact_calls.append((fact_id, tenant_id))
        # Return a mock fact if tenant matches AND fact_id matches 123
        if tenant_id == "authorized-tenant" and fact_id == 123:
            from unittest.mock import MagicMock

            mock_fact = MagicMock()
            mock_fact.tenant_id = tenant_id
            mock_fact.project = "alpha"
            mock_fact.to_dict.return_value = {
                "id": fact_id,
                "tenant_id": tenant_id,
                "project": "alpha",
                "content": "Secret content",
                "fact_type": "knowledge",
                "tags": [],
                "confidence": "C3",
                "valid_from": None,
                "valid_until": None,
                "source": "api",
                "meta": {},
                "created_at": "2026-06-30T16:00:00Z",
                "updated_at": "2026-06-30T16:00:00Z",
                "tx_id": None,
                "consensus_score": 1.0,
            }
            return mock_fact
        return None

    async def deprecate(
        self,
        fact_id: int,
        reason: str | None = None,
        conn=None,
        tenant_id: str = "default",
    ) -> bool:
        self.deprecate_calls.append((fact_id, reason, tenant_id))
        return True


def test_delete_fact_scopes_to_authenticated_tenant() -> None:
    fake_engine = _FakeAsyncEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}",
        "DELETE",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}", "DELETE"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="authorized-tenant",
        permissions=["write"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    # 1. Try to delete a fact owned by the authorized tenant (should succeed)
    with TestClient(app) as client:
        response = client.delete("/v1/facts/123")
    assert response.status_code == 200
    assert fake_engine.get_fact_calls == [(123, "authorized-tenant")]
    assert fake_engine.deprecate_calls == [(123, "api deprecated", "authorized-tenant")]

    # Reset calls
    fake_engine.get_fact_calls.clear()
    fake_engine.deprecate_calls.clear()

    # 2. Try to delete a fact when engine.get_fact returns None (e.g. not owned by authorized tenant)
    # The route should return 404
    with TestClient(app) as client:
        response = client.delete("/v1/facts/999")
    assert response.status_code == 404
    assert fake_engine.get_fact_calls == [(999, "authorized-tenant")]
    assert fake_engine.deprecate_calls == []


def test_delete_memory_scopes_to_authenticated_tenant() -> None:
    fake_engine = _FakeAsyncEngine()

    app = FastAPI()
    app.include_router(memories_router.router)
    auth_dep = _dependency_for(
        "/v1/memories/{memory_id}",
        "DELETE",
        _route_by_path(memories_router.router, "/v1/memories/{memory_id}", "DELETE"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="authorized-tenant",
        permissions=["write"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    # 1. Try to delete a memory owned by the authorized tenant (should succeed)
    with TestClient(app) as client:
        response = client.delete("/v1/memories/123")
    assert response.status_code == 200
    assert fake_engine.get_fact_calls == [(123, "authorized-tenant")]
    assert fake_engine.deprecate_calls == [(123, "api_deleted", "authorized-tenant")]

    # Reset calls
    fake_engine.get_fact_calls.clear()
    fake_engine.deprecate_calls.clear()

    # 2. Try to delete a memory not owned by the authorized tenant (should fail with 404)
    with TestClient(app) as client:
        response = client.delete("/v1/memories/999")
    assert response.status_code == 404
    assert fake_engine.get_fact_calls == [(999, "authorized-tenant")]
    assert fake_engine.deprecate_calls == []
