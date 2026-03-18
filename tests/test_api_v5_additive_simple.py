import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from cortex.api.core import app
from cortex.api.deps import get_async_engine
from cortex.auth.deps import require_permission, require_auth

# Mock AuthResult for dependency override
mock_auth = MagicMock()
mock_auth.tenant_id = "default"
mock_auth.authenticated = True
mock_auth.permissions = ["read", "write", "admin"]

async def override_auth():
    return mock_auth

@pytest.fixture
def mock_engine():
    engine = AsyncMock()
    # Mock history/causal chain
    engine.get_causal_chain.return_value = [
        {"id": 1, "project": "test", "content": "v1", "fact_type": "knowledge", "created_at": "2024-01-01"},
        {"id": 2, "project": "test", "content": "v2", "fact_type": "knowledge", "created_at": "2024-01-02"},
    ]
    # Mock taint report
    report = MagicMock()
    report.source_fact_id = 99
    report.affected_count = 2
    report.confidence_changes = [{"fact_id": 100, "old": "C5", "new": "C3"}]
    engine.propagate_taint.return_value = report
    
    # Mock trust registry
    registry = MagicMock()
    profile = MagicMock()
    profile.agent_id = "test_agent"
    profile.successes = 10
    profile.failures = 1
    profile.taint_events = 0
    profile.last_success_ts = None
    profile.last_incident_ts = None
    registry.get_profile.return_value = profile
    registry.compute_trust_score.return_value = 0.9
    engine.get_trust_registry.return_value = registry
    
    # Mock ledger verify and stats
    engine.verify_ledger.return_value = {"valid": True}
    engine.stats.return_value = {"causal_facts": 10, "active_facts": 10}
    
    return engine

@pytest.fixture
def client(mock_engine):
    app.dependency_overrides[get_async_engine] = lambda: mock_engine
    
    # Define a helper that returns our mock_auth for ANY permission level
    def get_override(perm):
        return override_auth

    # Override the specific dependency factories
    app.dependency_overrides[require_auth] = override_auth
    # require_permission is a factory, we need to override the SPECIFIC instances used in routes
    # But since we can't easily guess all instances, we override the common ones.
    # The actual routes use Depends(require_permission("read")), etc.
    # FastAPI keys these by the function object and its arguments.
    for perm in ["read", "write", "admin"]:
        app.dependency_overrides[require_permission(perm)] = override_auth
    
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_fact_history_endpoint(client):
    resp = client.get("/v1/facts/1/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

def test_taint_propagation_endpoint(client):
    resp = client.post("/v1/facts/99/taint")
    assert resp.status_code == 200
    assert resp.json()["source_id"] == 99

def test_trust_endpoints(client):
    # Test agent profile
    resp = client.get("/v1/trust/profiles/test_agent")
    assert resp.status_code == 200
    assert resp.json()["agent_id"] == "test_agent"
    
    # Test compliance report
    resp = client.get("/v1/trust/compliance")
    assert resp.status_code == 200
    assert resp.json()["article_12_status"] == "LOGGED_AND_VERIFIED"
