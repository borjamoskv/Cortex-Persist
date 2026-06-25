import pytest
from fastapi.testclient import TestClient
from legacy_research.extensions.ouroboros.ouroboros_agent import app, engine

@pytest.fixture(autouse=True)
def setup_test_engine(tmp_path):
    # Re-initialize ledger path for testing to avoid cluttering the workspace
    log_file = tmp_path / "daemon_audit.jsonl"
    engine.ledger.log_path = str(log_file)
    engine.ledger._initialize_log()

def test_daemon_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "health_score" in data
    assert "active_version" in data
    assert "cycle_count" in data
    assert "state_hash" in data
    assert "identity_anchor" in data
    
    assert data["identity_anchor"] == "C5-REAL-MYTHOS-1"

def test_daemon_metrics_endpoint():
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_microjoules" in data
    assert "current_exergy_score" in data
    assert "temperature_mc" in data

def test_daemon_ledger_endpoint():
    client = TestClient(app)
    response = client.get("/ledger")
    assert response.status_code == 200
    
    data = response.json()
    assert "log_path" in data
    assert "events" in data
