from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cortex.auth.deps import require_auth, require_permission
from cortex.routes import swarm as swarm_router

# Mock AuthResult
mock_auth = MagicMock()
mock_auth.tenant_id = "default"
mock_auth.authenticated = True
mock_auth.permissions = ["read", "write", "admin"]
mock_auth.key_name = "test_agent"


async def override_auth():
    return mock_auth


@pytest.fixture
async def client():
    app = FastAPI()
    manager = _FakeSwarmManager()
    app.state.swarm_manager = manager
    app.include_router(swarm_router.router)

    # Override permissions
    app.dependency_overrides[require_auth] = override_auth
    for perm in ["read", "write", "admin"]:
        app.dependency_overrides[require_permission(perm)] = override_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, manager

    app.dependency_overrides.clear()


class _FakeSwarmManager:
    def __init__(self) -> None:
        self._state = SimpleNamespace(
            id="wt-1",
            branch_name="test_branch",
            path="/tmp/wt_test",
            status="active",
            created_at="2026-04-14T00:00:00Z",
        )

    async def get_status(self):
        return {
            "active_worktrees": 1,
            "total_worktrees": 1,
            "agent_pids": [1234],
            "timestamp": "2026-04-14T00:00:00Z",
        }

    async def create_worktree(self, branch_name: str, base_path: str | None):
        self._state.branch_name = branch_name
        if base_path:
            self._state.path = base_path
        return self._state

    async def get_worktree(self, worktree_id: str):
        if worktree_id != self._state.id:
            return None
        return self._state

    async def delete_worktree(self, worktree_id: str):
        return worktree_id == self._state.id


@pytest.mark.asyncio
async def test_swarm_worktree_lifecycle_api(client):
    client, _manager = client
    # 1. Status
    resp = await client.get("/v1/swarm/status")
    assert resp.status_code == 200
    assert "active_worktrees" in resp.json()

    # 2. Create
    resp = await client.post("/v1/swarm/worktrees", json={"branch_name": "test_branch"})
    assert resp.status_code == 200
    data = resp.json()
    wt_id = data["id"]
    assert data["status"] in ["active", "provisioning"]

    # 3. Get Status
    resp = await client.get(f"/v1/swarm/worktrees/{wt_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == wt_id

    # 4. Delete
    resp = await client.delete(f"/v1/swarm/worktrees/{wt_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "tearing_down"
