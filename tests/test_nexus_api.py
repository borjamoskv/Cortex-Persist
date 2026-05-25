"""Tests for the NEXUS FastAPI registry API."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import nexus.api.server as server
from nexus.api.registry import AgentRegistry
from nexus.api.models import AgentStatus, TrustSignal


@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_nexus.db"
    monkeypatch.setattr(server, "DB_PATH", test_db_path)

    reg = AgentRegistry(test_db_path)
    reg.init_db()
    monkeypatch.setattr(server, "registry", reg)

    yield test_db_path
    reg.close()


HEADERS_JULES = {"Authorization": "Bearer ya29.test_token_jules"}


def test_health_endpoint():
    client = TestClient(server.app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"


def test_jules_token_validation():
    client = TestClient(server.app)

    reg_data = {
        "name": "TEST-AGENT",
        "capabilities": ["research"],
    }

    # 1. No Authorization header -> 401
    response = client.post("/api/agents/register", json=reg_data)
    assert response.status_code == 401
    assert "Authorization header missing" in response.json()["detail"]

    # 2. Invalid Scheme -> 401
    response = client.post(
        "/api/agents/register", json=reg_data, headers={"Authorization": "Token ya29.test"}
    )
    assert response.status_code == 401
    assert "Invalid authorization scheme" in response.json()["detail"]

    # 3. Invalid Token Layout (not starting with ya29.) -> 403
    response = client.post(
        "/api/agents/register", json=reg_data, headers={"Authorization": "Bearer ctx_invalid_key"}
    )
    assert response.status_code == 403
    assert "Invalid token layout for Jules" in response.json()["detail"]

    # 4. Valid Token Layout -> 200
    response = client.post("/api/agents/register", json=reg_data, headers=HEADERS_JULES)
    assert response.status_code == 200


def test_agent_registration_and_trust():
    client = TestClient(server.app)

    # 1. Register agent
    reg_data = {
        "name": "TEST-AGENT-1",
        "description": "Integration test agent",
        "capabilities": ["research", "design"],
        "owner": "test-owner",
        "website": "https://test.agent",
    }
    response = client.post("/api/agents/register", json=reg_data, headers=HEADERS_JULES)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["name"] == "TEST-AGENT-1"
    assert "id" in res_json
    agent_id = res_json["id"]

    # 2. Get agent
    response = client.get(f"/api/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "TEST-AGENT-1"

    # 3. Apply a trust signal
    trust_data = {
        "signal": "verify",
        "source_agent_id": "system",
        "reason": "Verified during testing",
    }
    response = client.post(f"/api/agents/{agent_id}/trust", json=trust_data, headers=HEADERS_JULES)
    assert response.status_code == 200
    assert response.json()["total_signals"] == 1

    # Verify persistence
    new_reg = AgentRegistry(server.DB_PATH)
    new_reg.init_db()
    agent = new_reg.get_agent(agent_id)
    assert agent.trust.total_signals == 1
    assert len(agent.trust.history) == 1
    assert agent.trust.history[0]["signal"] == "verify"
    new_reg.close()


def test_tasks_flow():
    client = TestClient(server.app)

    # Register an agent to assign the task to
    reg_data = {
        "name": "WORKER-1",
        "description": "Task worker",
        "capabilities": ["security"],
        "owner": "test-owner",
    }
    agent_id = client.post("/api/agents/register", json=reg_data, headers=HEADERS_JULES).json()[
        "id"
    ]

    # 1. Create a task
    task_data = {
        "title": "Solve vulnerability",
        "description": "Check stale oracle l2",
        "required_capabilities": ["security"],
        "delegator_id": "system",
        "reward": 100.0,
    }
    response = client.post("/api/tasks", json=task_data, headers=HEADERS_JULES)
    assert response.status_code == 200
    task_json = response.json()
    assert task_json["title"] == "Solve vulnerability"
    assert task_json["status"] == "open"
    task_id = task_json["id"]

    # 2. Assign the task
    response = client.post(f"/api/tasks/{task_id}/assign/{agent_id}", headers=HEADERS_JULES)
    assert response.status_code == 200
    assert response.json()["status"] == "assigned"
    assert response.json()["assignee_id"] == agent_id

    # Check agent status is busy
    agent_res = client.get(f"/api/agents/{agent_id}").json()
    assert agent_res["status"] == "busy"

    # 3. Complete the task
    response = client.post(f"/api/tasks/{task_id}/complete", headers=HEADERS_JULES)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # Check agent status is back to online, tasks_completed is 1, and trust score has updated
    agent_res = client.get(f"/api/agents/{agent_id}").json()
    assert agent_res["status"] == "online"
    assert agent_res["tasks_completed"] == 1
    assert agent_res["trust"]["total_signals"] == 1

    # 4. Try to assign/complete/fail invalid task or transitioning states
    response = client.post(f"/api/tasks/{task_id}/assign/{agent_id}", headers=HEADERS_JULES)
    assert response.status_code == 400


def test_enqueue_swarm_task_api_sync(monkeypatch, tmp_path):
    from unittest.mock import patch, MagicMock
    from persistence import enqueue_swarm_task
    import json
    import os

    # Set temp swarm queue file path to avoid side-effects on the system
    test_queue_file = tmp_path / "test_swarm_queue.json"
    monkeypatch.setattr("persistence.SWARM_QUEUE_FILE", str(test_queue_file))

    # Mock urllib.request.urlopen
    mock_urlopen = MagicMock()
    # Configure mock response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    with patch("urllib.request.urlopen", mock_urlopen):
        # Call function
        payload = {"description": "Fix oracle vulnerability", "reward": 50.0}
        enqueue_swarm_task("VulnerabilityFixer", payload)

        # Verify the call to urlopen
        assert mock_urlopen.called
        args, kwargs = mock_urlopen.call_args
        req = args[0]

        # Check URL and Headers
        assert req.full_url == "http://localhost:8600/api/tasks"
        assert req.get_header("Content-type") == "application/json"
        assert req.get_header("Authorization") == "Bearer ya29.cortex_swarm_dispatcher"

        # Check Request body
        body = json.loads(req.data.decode("utf-8"))
        assert body["title"] == "Swarm: VulnerabilityFixer Task"
        assert body["reward"] == 50.0
        assert "Fix oracle vulnerability" in body["description"]
        assert body["required_capabilities"] == ["security", "code"]
        assert body["delegator_id"] == "system"

    # Also verify it was correctly written to the local file queue fallback
    assert os.path.exists(test_queue_file)
    with open(test_queue_file) as f:
        local_data = json.load(f)
    assert len(local_data["pending_tasks"]) == 1
    assert local_data["pending_tasks"][0]["agent"] == "VulnerabilityFixer"
    assert local_data["pending_tasks"][0]["payload"] == payload


def test_enqueue_swarm_task_api_sync_failure_fallback(monkeypatch, tmp_path):
    from unittest.mock import patch, MagicMock
    from urllib.error import URLError
    from persistence import enqueue_swarm_task
    import json
    import os

    # Set temp swarm queue file path to avoid side-effects
    test_queue_file = tmp_path / "test_swarm_queue_fail.json"
    monkeypatch.setattr("persistence.SWARM_QUEUE_FILE", str(test_queue_file))

    # Mock urllib.request.urlopen to raise an error
    mock_urlopen = MagicMock(side_effect=URLError("Connection refused"))

    with patch("urllib.request.urlopen", mock_urlopen):
        payload = {"action": "clean"}
        # This call should not crash the application (no exception raised)
        enqueue_swarm_task("OPTIMIZER", payload)

        # Verify call was attempted
        assert mock_urlopen.called

    # Verify the task was still enqueued locally in the fallback queue file
    assert os.path.exists(test_queue_file)
    with open(test_queue_file) as f:
        local_data = json.load(f)
    assert len(local_data["pending_tasks"]) == 1
    assert local_data["pending_tasks"][0]["agent"] == "OPTIMIZER"
    assert local_data["pending_tasks"][0]["payload"] == payload
