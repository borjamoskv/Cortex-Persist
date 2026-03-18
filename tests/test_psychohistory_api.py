from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from cortex.api.core import app
from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.extensions.swarm.psychohistory import AGENT_BIASES
from cortex.utils.result import Ok

# Mock Auth
mock_auth = AuthResult("test_key", "test_hash")
mock_auth.authenticated = True
mock_auth.permissions = ["read", "write", "admin"]


async def override_auth():
    return mock_auth


@pytest.fixture
def mock_engine():
    engine = AsyncMock()
    # Mock LLM router
    router = AsyncMock()
    # Return Ok("Simulated cascade effect") for individual agents
    # Return Ok("O(1) Contingency Crystal") for synthesis
    router.execute_resilient.side_effect = lambda prompt: Ok(
        "O(1) Contingency Crystal" if "Hari Seldon" in prompt.system_instruction else "Simulated cascade effect"
    )
    engine.get_router.return_value = router
    engine.store.return_value = None
    return engine


@pytest.fixture
async def client(mock_engine):
    app.dependency_overrides[get_async_engine] = lambda: mock_engine
    
    for perm in ["read", "write", "admin"]:
        app.dependency_overrides[require_permission(perm)] = override_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_psychohistory_simulation_api(client, mock_engine):
    payload = {
        "scenario_name": "Apagón Satelital Test",
        "simulated_years": 10,
        "project": "TEST_PROJECT"
    }

    resp = await client.post("/v1/swarm/psychohistory", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["scenario"] == "Apagón Satelital Test"
    assert data["simulated_years"] == 10
    assert data["active_agents"] == len(AGENT_BIASES)  # Should be 50
    assert data["contingency_crystal"] == "O(1) Contingency Crystal"
    # Given all mocked responses succeed, resonance should be quite high (0.85-0.95 range due to logic)
    assert data["resonance"] > 0

    # Verify that the engine.store was called to persist the crystal
    mock_engine.store.assert_called_once()
    store_kwargs = mock_engine.store.call_args.kwargs
    assert store_kwargs["project"] == "TEST_PROJECT"
    assert store_kwargs["content"] == "O(1) Contingency Crystal"
    assert store_kwargs["fact_type"] == "bridge"
    assert store_kwargs["confidence"] == "C5"
    assert store_kwargs["source"] == "swarm:psychohistory"
    assert store_kwargs["meta"]["scenario"] == "Apagón Satelital Test"
