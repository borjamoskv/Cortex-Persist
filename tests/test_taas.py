# [C5-REAL] Exergy-Maximized
import pytest
from httpx import ASGITransport, AsyncClient

from cortex.api.core import app
from cortex.api.deps import get_async_engine
from legacy_research.auth.deps import require_auth, require_permission
from unittest.mock import MagicMock, AsyncMock

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
    return AsyncMock()


@pytest.fixture
async def ac_client(mock_engine):
    app.dependency_overrides[get_async_engine] = lambda: mock_engine
    app.dependency_overrides[require_auth] = override_auth
    for perm in ["read", "write", "admin"]:
        app.dependency_overrides[require_permission(perm)] = override_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_taas_quote(ac_client):
    ac = ac_client
    req_data = {
        "task_type": "audit_contract",
        "payload": {"contract_address": "0x123..."},
        "sla": {
            "confidence_level": "C5-REAL",
            "max_latency_ms": 1000,
            "requires_zk_proof": True,
        },
    }
    response = await ac.post("/v1/taas/jobs/quote", json=req_data)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "estimated_cost_credits" in data
    assert "estimated_time_ms" in data
    assert data["estimated_cost_credits"] > 0


@pytest.mark.asyncio
async def test_taas_execute_and_verify(ac_client):
    ac = ac_client
    # 1. Quote
    req_data = {
        "task_type": "verify_state",
        "payload": {"state_hash": "abc..."},
        "sla": {
            "confidence_level": "C3-SIM",
            "max_latency_ms": 500,
            "requires_zk_proof": True,
        },
    }
    quote_res = await ac.post("/v1/taas/jobs/quote", json=req_data)
    assert quote_res.status_code == 200
    job_id = quote_res.json()["job_id"]

    # 2. Execute
    exec_res = await ac.post(f"/v1/taas/jobs/{job_id}/execute")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "COMPLETED"
    assert exec_data["job_id"] == job_id

    # 3. Verify
    proof = exec_data.get("proof")
    verify_res = await ac.get(f"/v1/taas/jobs/{job_id}/verify", params={"proof": str(proof)})
    assert verify_res.status_code == 200
    assert verify_res.json()["verified"] is True
