from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.agents.builtins.verification_agent import VerificationAgent
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import MessageKind, new_message


@pytest.fixture
def mock_manifest():
    return AgentManifest(agent_id="verifier", purpose="Verification of agent actions")


@pytest.fixture
def mock_bus():
    return AsyncMock()


@pytest.fixture
def mock_registry():
    return MagicMock()


@pytest.fixture
def agent(mock_manifest, mock_bus, mock_registry):
    return VerificationAgent(mock_manifest, mock_bus, mock_registry)


@pytest.mark.asyncio
async def test_handle_v2_request(agent, mock_bus):
    payload = {
        "subject": "plan_step",
        "candidate": {"objective": "Test objective with enough length", "steps": ["Step 1"]},
    }
    msg = new_message(
        sender="sender",
        recipient="verifier",
        kind=MessageKind.TASK_REQUEST,
        payload=payload,
    )

    await agent.handle_message(msg)

    # Check if a reply was sent
    assert mock_bus.send.called
    reply = mock_bus.send.call_args[0][0]
    assert reply.kind == MessageKind.TASK_RESULT
    assert reply.payload["ok"] is True
    assert reply.payload["verdict"] == "accepted"


@pytest.mark.asyncio
async def test_handle_legacy_request(agent, mock_bus):
    payload = {"code": "print('fixed')"}
    msg = new_message(
        sender="sender",
        recipient="verifier",
        kind=MessageKind.TASK_REQUEST,
        payload=payload,
    )

    await agent.handle_message(msg)

    assert mock_bus.send.called
    reply = mock_bus.send.call_args[0][0]
    # For legacy to pass, we need to ensure the oracle result is ok
    assert reply.payload["ok"] is True


@pytest.mark.asyncio
async def test_handle_invalid_request(agent, mock_bus):
    payload = {"garbage": "data"}
    msg = new_message(
        sender="sender",
        recipient="verifier",
        kind=MessageKind.TASK_REQUEST,
        payload=payload,
    )
    await agent.handle_message(msg)

    assert mock_bus.send.called
    reply = mock_bus.send.call_args[0][0]
    assert "error" in reply.payload
