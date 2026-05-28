from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine, get_engine
from cortex.auth.models import AuthResult
from cortex.routes import admin as admin_router
from cortex.routes import memories as memories_router
from cortex.routes import swarm as swarm_router


def _override_auth(tenant_id: str, permissions: list[str]):
    return lambda: AuthResult(authenticated=True, tenant_id=tenant_id, permissions=permissions)


def _route_dependency(router, path: str, method: str):
    for route in router.routes:
        if route.path == path and method in route.methods:
            return route.dependant.dependencies[0].call
    raise AssertionError(f"Route not found: {method} {path}")


def _override_route_auth(app: FastAPI, router, path: str, method: str, tenant_id: str, permissions: list[str]) -> None:
    for route in router.routes:
        if route.path == path and method in route.methods:
            for dep in route.dependant.dependencies:
                if dep.call not in {get_engine, get_async_engine, swarm_router.get_manager}:
                    app.dependency_overrides[dep.call] = _override_auth(tenant_id, permissions)
            return
    raise AssertionError(f"Route not found: {method} {path}")


def test_memories_verify_scopes_to_authenticated_tenant() -> None:
    observed: dict[str, str] = {}

    class FakeEngine:
        async def verify_ledger(self, tenant_id: str | None = None):
            observed["tenant_id"] = str(tenant_id)
            return {"valid": True, "violations": [], "tx_count": 4}

    app = FastAPI()
    app.include_router(memories_router.router)
    _override_route_auth(app, memories_router.router, "/v1/memories/verify", "GET", "tenant-a", ["read"])
    app.dependency_overrides[get_async_engine] = lambda: FakeEngine()

    with TestClient(app) as client:
        response = client.get("/v1/memories/verify")

    assert response.status_code == 200
    assert observed == {"tenant_id": "tenant-a"}


def test_swarm_routes_hide_other_tenant_worktrees() -> None:
    class FakeManager:
        def __init__(self) -> None:
            self.worktrees = {
                "wt-a": SimpleNamespace(id="wt-a", branch_name="a", path=Path("/tmp/a"), status="active", created_at="2026-01-01", pid=11),
                "wt-b": SimpleNamespace(id="wt-b", branch_name="b", path=Path("/tmp/b"), status="active", created_at="2026-01-01", pid=22),
            }

        async def get_status(self):
            return {"timestamp": "2026-01-01T00:00:00Z"}

        async def create_worktree(self, branch_name: str):
            state = SimpleNamespace(id="wt-new", branch_name=branch_name, path=Path("/tmp/new"), status="active", created_at="2026-01-01", pid=33)
            self.worktrees[state.id] = state
            return state

        async def get_worktree(self, worktree_id: str):
            return self.worktrees.get(worktree_id)

        async def delete_worktree(self, worktree_id: str):
            return worktree_id in self.worktrees

    app = FastAPI()
    app.include_router(swarm_router.router)
    app.state.swarm_manager = FakeManager()
    app.state.swarm_worktree_owners = {"wt-a": "tenant-a", "wt-b": "tenant-b"}

    for path, method, perms in [
        ("/v1/swarm/status", "GET", ["read"]),
        ("/v1/swarm/worktrees/{worktree_id}", "GET", ["read"]),
        ("/v1/swarm/worktrees/{worktree_id}", "DELETE", ["admin"]),
        ("/v1/swarm/worktrees", "POST", ["write"]),
    ]:
        _override_route_auth(app, swarm_router.router, path, method, "tenant-a", perms)

    with TestClient(app) as client:
        status = client.get("/v1/swarm/status")
        foreign = client.get("/v1/swarm/worktrees/wt-b")
        own = client.get("/v1/swarm/worktrees/wt-a")

    assert status.status_code == 200
    assert status.json()["total_worktrees"] == 1
    assert foreign.status_code == 404
    assert own.status_code == 200


def test_admin_handoff_passes_authenticated_tenant(monkeypatch) -> None:
    observed: dict[str, object] = {}

    async def fake_generate_handoff(engine, session_meta=None, tenant_id: str = "default"):
        observed["tenant_id"] = tenant_id
        observed["session_meta"] = session_meta
        return {"tenant_id": tenant_id, "hot_decisions": []}

    import cortex.extensions.agents.handoff as handoff_module

    monkeypatch.setattr(handoff_module, "generate_handoff", fake_generate_handoff)
    monkeypatch.setattr(handoff_module, "save_handoff", lambda data: None)

    app = FastAPI()
    app.include_router(admin_router.router)
    _override_route_auth(app, admin_router.router, "/v1/handoff", "POST", "tenant-a", ["read"])
    app.dependency_overrides[get_engine] = lambda: object()

    with TestClient(app) as client:
        response = client.post("/v1/handoff", json={"session": {"focus_projects": ["alpha"]}})

    assert response.status_code == 200
    assert observed == {"tenant_id": "tenant-a", "session_meta": {"focus_projects": ["alpha"]}}
