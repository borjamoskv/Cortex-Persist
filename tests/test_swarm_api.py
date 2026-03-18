import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from cortex.api.core import app
from cortex.auth.deps import require_permission

# Mock AuthResult
mock_auth = MagicMock()
mock_auth.tenant_id = "default"
mock_auth.authenticated = True
mock_auth.permissions = ["read", "write", "admin"]

async def override_auth():
    return mock_auth

@pytest.fixture
def client():
    # Override permissions
    # We must override the specific instances return by require_permission("read"), etc.
    from cortex.auth.deps import require_permission, require_auth
    app.dependency_overrides[require_auth] = override_auth
    for perm in ["read", "write", "admin"]:
        app.dependency_overrides[require_permission(perm)] = override_auth
    
    yield TestClient(app)
    app.dependency_overrides.clear()

@patch("cortex.extensions.swarm.manager.isolated_worktree")
def test_swarm_worktree_lifecycle_api(mock_iso, client):
    # Mock context manager
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = "/tmp/wt_test"
    mock_ctx.__aexit__.return_value = None
    mock_iso.return_value = mock_ctx
    
    # 1. Status
    resp = client.get("/v1/swarm/status")
    assert resp.status_code == 200
    assert "active_worktrees" in resp.json()

    # 2. Create
    resp = client.post("/v1/swarm/worktrees", json={
        "branch_name": "test_branch"
    })
    assert resp.status_code == 200
    data = resp.json()
    wt_id = data["id"]
    assert data["status"] in ["active", "provisioning"]

    # 3. Get Status
    resp = client.get(f"/v1/swarm/worktrees/{wt_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == wt_id

    # 4. Delete
    resp = client.delete(f"/v1/swarm/worktrees/{wt_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "tearing_down"
