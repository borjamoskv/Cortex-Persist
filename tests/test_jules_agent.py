"""Tests for cortex.agents.builtins.jules_agent — JulesAgent."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from cortex.agents.builtins.jules_agent import JulesAgent, create_jules_agent
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry


class MockBus:
    """Lightweight mock bus implementing the MessageBus protocol."""

    def __init__(self) -> None:
        self.sent: list[AgentMessage] = []

    async def send(self, message: AgentMessage) -> None:
        self.sent.append(message)

    async def receive(self, agent_id: str, timeout: float = 1.0) -> AgentMessage | None:
        return None

    async def broadcast(self, message: AgentMessage) -> None:
        pass

    async def close(self) -> None:
        pass


@pytest.fixture
def bus() -> MockBus:
    return MockBus()


@pytest.fixture
def agent(bus: MockBus) -> JulesAgent:
    return create_jules_agent(bus, api_key="test-key-fake")


class TestJulesAgentFactory:
    def test_creates_agent(self, bus: MockBus) -> None:
        agent = create_jules_agent(bus, api_key="test-key")
        assert agent.agent_id == "jules-bridge"
        assert agent.manifest.can_delegate is True

    def test_manifest_defaults(self, bus: MockBus) -> None:
        agent = create_jules_agent(bus, api_key="k")
        assert agent.manifest.confidence_floor == "C4"
        assert agent.manifest.max_consecutive_errors == 5


class TestJulesAgentDispatch:
    @pytest.mark.asyncio
    async def test_unsupported_op(self, agent: JulesAgent, bus: MockBus) -> None:
        msg = new_message(
            sender="test-sender",
            recipient="jules-bridge",
            kind=MessageKind.TASK_REQUEST,
            payload={"op": "nonexistent"},
        )

        agent._client = AsyncMock()
        await agent.handle_message(msg)

        assert len(bus.sent) == 1
        assert "unsupported op" in bus.sent[0].payload.get("error", "")

    @pytest.mark.asyncio
    async def test_dispatch_op(self, agent: JulesAgent) -> None:
        """Test dispatch op calls create_session correctly."""
        mock_client = AsyncMock()
        mock_client.create_session.return_value = {
            "name": "sessions/42",
            "state": "ACTIVE",
        }
        agent._client = mock_client

        result = await agent._op_dispatch({
            "prompt": "Fix all tests",
            "owner": "borjamoskv",
            "repo": "Cortex-Persist",
            "branch": "dev",
        })

        assert result["session_id"] == "42"
        assert "jules.google.com" in result["web_url"]
        mock_client.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_missing_prompt(self, agent: JulesAgent) -> None:
        agent._client = AsyncMock()

        with pytest.raises(ValueError, match="prompt"):
            await agent._op_dispatch({})

    @pytest.mark.asyncio
    async def test_status_op(self, agent: JulesAgent) -> None:
        mock_client = AsyncMock()
        mock_client.get_session.return_value = {
            "state": "COMPLETED",
            "title": "Test",
        }
        agent._client = mock_client

        result = await agent._op_status({"session_id": "99"})

        assert result["state"] == "COMPLETED"
        mock_client.get_session.assert_called_once_with("99")

    @pytest.mark.asyncio
    async def test_message_op(self, agent: JulesAgent) -> None:
        mock_client = AsyncMock()
        mock_client.send_message.return_value = {}
        agent._client = mock_client

        result = await agent._op_message({
            "session_id": "99",
            "message": "do more",
        })

        assert result["sent"] is True
        mock_client.send_message.assert_called_once_with("99", "do more")

    @pytest.mark.asyncio
    async def test_approve_op(self, agent: JulesAgent) -> None:
        mock_client = AsyncMock()
        mock_client.approve_plan.return_value = {}
        agent._client = mock_client

        result = await agent._op_approve({"session_id": "99"})

        assert result["approved"] is True

    @pytest.mark.asyncio
    async def test_list_op(self, agent: JulesAgent) -> None:
        mock_client = AsyncMock()
        mock_client.list_sessions.return_value = {
            "sessions": [
                {"name": "sessions/1", "title": "A", "state": "COMPLETED", "prompt": "x"},
                {"name": "sessions/2", "title": "B", "state": "ACTIVE", "prompt": "y"},
            ]
        }
        agent._client = mock_client

        result = await agent._op_list({"page_size": 5})

        assert result["count"] == 2
        mock_client.list_sessions.assert_called_once_with(page_size=5)

    @pytest.mark.asyncio
    async def test_client_not_initialized(self, agent: JulesAgent, bus: MockBus) -> None:
        """Verify error when client is None."""
        msg = new_message(
            sender="test",
            recipient="jules-bridge",
            kind=MessageKind.TASK_REQUEST,
            payload={"op": "list"},
        )
        agent._client = None
        await agent.handle_message(msg)

        assert len(bus.sent) == 1
        assert "not initialized" in bus.sent[0].payload.get("error", "")
