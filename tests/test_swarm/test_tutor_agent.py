from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import MessageKind
from cortex.extensions.swarm.tutor import TutorAgent


@pytest.fixture
def manifest():
    return AgentManifest(agent_id="TUTOR-META", purpose="x10 Governance enforcing the Eight Laws")


@pytest.fixture
def db_conn():
    return AsyncMock()


@pytest.fixture
def mock_bus():
    bus = AsyncMock()
    bus.send = AsyncMock()
    return bus


@pytest.mark.asyncio
async def test_tutor_agent_initialization(manifest, mock_bus, db_conn):
    tutor = TutorAgent(manifest, mock_bus, db_conn=db_conn)
    assert tutor.manifest.agent_id == "TUTOR-META"
    assert tutor._db_conn == db_conn


@pytest.mark.asyncio
async def test_tutor_deadlock_annihilation_warning(manifest, mock_bus):
    tutor = TutorAgent(manifest, mock_bus)

    # Mock the resolver to return a DEADLOCK_HEURISTIC
    tutor.conflict_resolver = MagicMock()
    mock_resolve = AsyncMock()
    mock_resolve.return_value = MagicMock(
        resolution=MagicMock(method="DEADLOCK_HEURISTIC"), to_dict=lambda: {"status": "resolved"}
    )
    tutor.conflict_resolver.resolve = mock_resolve

    agents_data = {"agent-A": {"specialty": "general"}, "agent-B": {"specialty": "general"}}
    options_data = [
        {"id": "opt1", "description": "do A", "proposer_id": "agent-A"},
        {"id": "opt2", "description": "do B", "proposer_id": "agent-B"},
    ]

    result = await tutor.settle_dispute("STRATEGIC", options_data, agents_data)
    assert result == {"status": "resolved"}
    # The warning log for deadlock annihilation should have been triggered internally


@pytest.mark.asyncio
async def test_tutor_annihilate_agent(manifest, mock_bus, db_conn, monkeypatch):
    tutor = TutorAgent(manifest, mock_bus, db_conn=db_conn)

    mock_graph = AsyncMock()
    mock_graph.propagate_taint.return_value = MagicMock(affected_count=5)

    # Patch the AsyncCausalGraph class
    monkeypatch.setattr("cortex.extensions.swarm.tutor.AsyncCausalGraph", lambda conn: mock_graph)

    await tutor._annihilate_agent("rogue-agent-x", last_fact_id=42, reason="Test quarantine")

    # Verify a shutdown message was sent to the supervisor
    mock_bus.send.assert_called_once()
    msg = mock_bus.send.call_args[0][0]
    assert msg.sender == "TUTOR-META"
    assert msg.recipient == "supervisor"
    assert msg.kind == MessageKind.TASK_REQUEST
    assert msg.payload["action"] == "quarantine"
    assert msg.payload["agent_id"] == "rogue-agent-x"

    # Verify taint propagation was triggered
    mock_graph.propagate_taint.assert_called_once_with(42)
