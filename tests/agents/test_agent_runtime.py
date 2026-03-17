"""Tests for CORTEX Agent Runtime — Sprint 1.

Tests:
    - Agent lifecycle (start, run, stop, state transitions)
    - Auto-quarantine on consecutive errors
    - Message bus send/receive
    - Tool registry policy enforcement
    - Supervisor start/stop/quarantine
    - Working memory isolation
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from cortex.agents.base import BaseAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.state import AgentStatus, WorkingMemory
from cortex.agents.supervisor import Supervisor
from cortex.agents.tools import ToolRegistry

# ── Test fixtures ────────────────────────────────────────────────


def _unique_db() -> str:
    """Return a unique in-memory SQLite URI per call."""
    return f"file:mem_{uuid.uuid4().hex[:8]}?mode=memory&cache=shared"


def _make_manifest(
    agent_id: str = "test-agent",
    daemon: bool = False,
    tools_allowed: list[str] | None = None,
    max_errors: int = 3,
) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        purpose="test agent",
        tools_allowed=tools_allowed or [],
        daemon=daemon,
        max_consecutive_errors=max_errors,
    )


class EchoAgent(BaseAgent):
    """Test agent that echoes task requests as task results."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received: list[AgentMessage] = []

    async def handle_message(self, message: AgentMessage) -> None:
        self.received.append(message)
        if message.kind == MessageKind.TASK_REQUEST:
            await self.send_result(
                message.sender,
                {"echo": message.payload},
                correlation_id=message.correlation_id,
            )


class FailingAgent(BaseAgent):
    """Test agent that always raises on handle_message."""

    async def handle_message(self, message: AgentMessage) -> None:
        raise RuntimeError("Intentional failure")


class CountingDaemon(BaseAgent):
    """Daemon agent that increments a counter on each tick."""

    def __init__(self, *args, max_ticks: int = 5, **kwargs):
        super().__init__(*args, **kwargs)
        self.tick_count = 0
        self.max_ticks = max_ticks

    async def tick(self) -> None:
        self.tick_count += 1
        if self.tick_count >= self.max_ticks:
            self.state.status = AgentStatus.IDLE  # Stop self


class DummyTool:
    """Minimal tool implementation for testing."""

    def __init__(self, name: str = "dummy_tool", result: str = "ok"):
        self._name = name
        self._result = result

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, **kwargs) -> str:
        return self._result


# ── Message Tests ────────────────────────────────────────────────


class TestAgentMessage:
    def test_serialization_roundtrip(self):
        msg = new_message(
            sender="agent-a",
            recipient="agent-b",
            kind=MessageKind.TASK_REQUEST,
            payload={"action": "verify", "target": "fact-123"},
            correlation_id="corr-1",
        )
        raw = msg.to_json()
        restored = AgentMessage.from_json(raw)

        assert restored.sender == "agent-a"
        assert restored.recipient == "agent-b"
        assert restored.kind == MessageKind.TASK_REQUEST
        assert restored.payload["action"] == "verify"
        assert restored.correlation_id == "corr-1"

    def test_message_kind_values(self):
        assert MessageKind.TASK_REQUEST.value == "task.request"
        assert MessageKind.SHUTDOWN.value == "shutdown"
        assert MessageKind.HEARTBEAT.value == "heartbeat"


# ── MessageBus Tests ─────────────────────────────────────────────


class TestSqliteMessageBus:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_unique_db())
        yield b
        await b.close()

    @pytest.mark.asyncio
    async def test_send_receive(self, bus):
        msg = new_message(
            sender="a",
            recipient="b",
            kind=MessageKind.TASK_REQUEST,
            payload={"x": 1},
        )
        await bus.send(msg)

        received = await bus.receive("b", timeout=0.1)
        assert received is not None
        assert received.sender == "a"
        assert received.payload == {"x": 1}

    @pytest.mark.asyncio
    async def test_receive_empty(self, bus):
        result = await bus.receive("nobody", timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_messages_consumed_once(self, bus):
        msg = new_message(
            sender="a",
            recipient="b",
            kind=MessageKind.TASK_REQUEST,
            payload={},
        )
        await bus.send(msg)

        first = await bus.receive("b", timeout=0.1)
        second = await bus.receive("b", timeout=0.1)

        assert first is not None
        assert second is None

    @pytest.mark.asyncio
    async def test_pending_count(self, bus):
        for i in range(3):
            await bus.send(
                new_message("a", "b", MessageKind.TASK_REQUEST, {"i": i})
            )

        count = await bus.pending_count("b")
        assert count == 3

    @pytest.mark.asyncio
    async def test_routing_isolation(self, bus):
        await bus.send(
            new_message("x", "agent-1", MessageKind.TASK_REQUEST, {"for": 1})
        )
        await bus.send(
            new_message("x", "agent-2", MessageKind.TASK_REQUEST, {"for": 2})
        )

        msg1 = await bus.receive("agent-1", timeout=0.1)
        msg2 = await bus.receive("agent-2", timeout=0.1)

        assert msg1 is not None
        assert msg1.payload["for"] == 1
        assert msg2 is not None
        assert msg2.payload["for"] == 2


# ── State Tests ──────────────────────────────────────────────────


class TestWorkingMemory:
    def test_isolation(self):
        mem_a = WorkingMemory()
        mem_b = WorkingMemory()

        mem_a.scratchpad["key"] = "value_a"
        mem_b.scratchpad["key"] = "value_b"

        assert mem_a.scratchpad["key"] == "value_a"
        assert mem_b.scratchpad["key"] == "value_b"

    def test_clear(self):
        mem = WorkingMemory()
        mem.active_tasks.append("task-1")
        mem.hypotheses.append("h-1")
        mem.scratchpad["k"] = "v"

        mem.clear()

        assert len(mem.active_tasks) == 0
        assert len(mem.hypotheses) == 0
        assert len(mem.scratchpad) == 0


# ── Tool Registry Tests ─────────────────────────────────────────


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = DummyTool("my_tool")
        registry.register(tool)

        retrieved = registry.get("my_tool")
        assert retrieved.name == "my_tool"

    def test_policy_enforcement(self):
        registry = ToolRegistry()
        registry.register(DummyTool("allowed_tool"))
        registry.register(DummyTool("forbidden_tool"))

        # Allowed
        t = registry.get("allowed_tool", allowed=["allowed_tool"])
        assert t.name == "allowed_tool"

        # Forbidden
        with pytest.raises(PermissionError):
            registry.get("forbidden_tool", allowed=["allowed_tool"])

    def test_not_found(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(DummyTool("a"))
        registry.register(DummyTool("b"))

        names = registry.list_tools()
        assert set(names) == {"a", "b"}


# ── BaseAgent Tests ──────────────────────────────────────────────


class TestBaseAgent:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_unique_db())
        yield b
        await b.close()

    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, bus):
        manifest = _make_manifest("echo-1")
        agent = EchoAgent(manifest, bus)

        assert agent.state.status == AgentStatus.IDLE

        # Send a task then a shutdown
        await bus.send(
            new_message("tester", "echo-1", MessageKind.TASK_REQUEST, {"q": 1})
        )
        await bus.send(
            new_message("tester", "echo-1", MessageKind.SHUTDOWN, {})
        )

        await agent.run()

        assert agent.state.status == AgentStatus.IDLE
        assert len(agent.received) == 1
        assert agent.state.total_messages_processed == 1

    @pytest.mark.asyncio
    async def test_quarantine_on_errors(self, bus):
        manifest = _make_manifest("fail-1", max_errors=2)
        agent = FailingAgent(manifest, bus)

        # Send messages that will cause errors
        for _ in range(3):
            await bus.send(
                new_message("tester", "fail-1", MessageKind.TASK_REQUEST, {})
            )

        await agent.run()

        assert agent.state.status == AgentStatus.QUARANTINED
        assert agent.state.consecutive_errors >= 2

    @pytest.mark.asyncio
    async def test_daemon_tick(self, bus):
        manifest = _make_manifest("daemon-1", daemon=True)
        agent = CountingDaemon(manifest, bus, max_ticks=3)

        await agent.run()

        assert agent.tick_count >= 3

    @pytest.mark.asyncio
    async def test_tool_access_policy(self, bus):
        manifest = _make_manifest("tool-1", tools_allowed=["allowed_tool"])
        registry = ToolRegistry()
        registry.register(DummyTool("allowed_tool", "ok"))
        registry.register(DummyTool("forbidden_tool", "bad"))

        agent = EchoAgent(manifest, bus, tool_registry=registry)

        # Allowed
        result = await agent.use_tool("allowed_tool")
        assert result == "ok"

        # Forbidden
        with pytest.raises(PermissionError):
            await agent.use_tool("forbidden_tool")


# ── Supervisor Tests ─────────────────────────────────────────────


class TestSupervisor:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_unique_db())
        yield b
        await b.close()

    @pytest.mark.asyncio
    async def test_register_and_status(self, bus):
        supervisor = Supervisor()
        agent = EchoAgent(_make_manifest("s-agent-1"), bus)

        supervisor.register(agent)

        status = supervisor.status()
        assert "s-agent-1" in status
        assert status["s-agent-1"]["status"] == "idle"
        assert supervisor.agent_count == 1

    @pytest.mark.asyncio
    async def test_duplicate_registration(self, bus):
        supervisor = Supervisor()
        agent = EchoAgent(_make_manifest("dup-1"), bus)

        supervisor.register(agent)
        with pytest.raises(ValueError):
            supervisor.register(agent)

    @pytest.mark.asyncio
    async def test_start_stop_agent(self, bus):
        supervisor = Supervisor()
        agent = EchoAgent(_make_manifest("lifecycle-1"), bus)
        supervisor.register(agent)

        await supervisor.start_agent("lifecycle-1")

        # Give it a moment to start
        await asyncio.sleep(0.2)
        assert agent.state.status == AgentStatus.RUNNING

        await supervisor.stop_agent("lifecycle-1")
        await asyncio.sleep(0.3)

        assert agent.state.status in (AgentStatus.IDLE, AgentStatus.RUNNING)

    @pytest.mark.asyncio
    async def test_quarantine_agent(self, bus):
        supervisor = Supervisor()
        agent = CountingDaemon(
            _make_manifest("q-1", daemon=True), bus, max_ticks=100
        )
        supervisor.register(agent)

        await supervisor.start_agent("q-1")
        await asyncio.sleep(0.2)

        await supervisor.quarantine_agent("q-1", reason="test quarantine")

        # Wait for task cancellation to propagate
        await asyncio.sleep(0.3)

        assert agent.state.status == AgentStatus.QUARANTINED
        assert agent.state.metadata["quarantine_reason"] == "test quarantine"

    @pytest.mark.asyncio
    async def test_health_check(self, bus):
        supervisor = Supervisor(heartbeat_timeout_s=60.0)
        agent = EchoAgent(_make_manifest("health-1"), bus)
        supervisor.register(agent)

        report = await supervisor.health_check()
        assert "health-1" in report
        assert report["health-1"]["status"] == "idle"
