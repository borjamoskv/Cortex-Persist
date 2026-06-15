# [C5-REAL] Exergy-Maximized
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cortex.api.core import app
from cortex.api.deps import get_async_engine
from cortex.auth.deps import require_auth, require_permission
from cortex.swarm.runtime import AgentRegistry, SubagentRunner

# Mock AuthResult
mock_auth = MagicMock()
mock_auth.tenant_id = "default"
mock_auth.authenticated = True
mock_auth.permissions = ["read", "write", "admin"]
mock_auth.key_name = "test_agent"


async def override_auth():
    return mock_auth


@pytest.fixture
def mock_engine():
    engine = AsyncMock()
    # Mock registration response to pass back name to identify v1/v2
    async def mock_register_agent(name, agent_type, public_key="", tenant_id=None):
        return f"fake-id-{name}"
    engine.register_agent.side_effect = mock_register_agent
    
    # Mock get_agent response
    async def mock_get_agent(agent_id, tenant_id=None):
        return {
            "id": agent_id,
            "name": "test-v1-agent" if "v1" in agent_id else "test-v2-agent",
            "agent_type": "ai" if "v1" in agent_id else "reasoning-agent",
            "reputation_score": 1.0,
            "created_at": "2026-06-15T18:00:00Z",
        }
    engine.get_agent.side_effect = mock_get_agent
    return engine


@pytest.fixture
async def client(mock_engine):
    # Setup App State for Swarm Registry
    registry = AgentRegistry()
    runner = SubagentRunner(registry)
    app.state.swarm_registry = registry
    app.state.swarm_runner = runner

    # Override permissions & engine dependency
    app.dependency_overrides[get_async_engine] = lambda: mock_engine
    app.dependency_overrides[require_auth] = override_auth
    for perm in ["read", "write", "admin"]:
        app.dependency_overrides[require_permission(perm)] = override_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_agent_v1(client):
    payload = {
        "name": "test-v1-agent",
        "agent_type": "ai",
        "public_key": "some-key"
    }
    resp = await client.post("/v1/agents", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test-v1-agent"
    assert "agent_id" in data


@pytest.mark.asyncio
async def test_register_agent_v2(client):
    # Register V2 agent
    payload = {
        "name": "test-v2-agent",
        "agent_type": "reasoning-agent",
        "public_key": "",
        "capabilities": ["reason", "tag:v2"],
        "kinds": ["reason"],
        "tags": ["v2"],
        "priority": 5,
    }
    resp = await client.post("/v2/agents", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test-v2-agent"

    # Verify that the agent was registered in the swarm_registry
    registry = app.state.swarm_registry
    resolved_name = registry.resolve("reason", require="test-v2-agent")
    assert resolved_name == "test-v2-agent"
