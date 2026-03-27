"""Tests for CORTEX Agent Runtime — Sprint 2: Builtin Agents.

Tests:
    - MemoryAgent: store, context, status ops
    - VerificationAgent: valid/invalid code, missing code
    - SecurityAgent: tick with/without threats, on-demand scan, escalation
    - HandoffAgent: save handoff request, load op, unknown op
    - NightshiftAgent: tick emits crystals, shutdown handling
    - SupervisorAgent: start/stop/quarantine/status/health ops
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.agents.builtins import (
    HandoffAgent,
    MemoryAgent,
    NightshiftAgent,
    SecurityAgent,
    SupervisorAgent,
    VerificationAgent,
)
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import MessageKind, new_message
from cortex.agents.supervisor import Supervisor

# ── Helpers ────────────────────────────────────────────────────────


def _uid() -> str:
    return f"file:mem_{uuid.uuid4().hex[:8]}?mode=memory&cache=shared"


def _manifest(
    agent_id: str = "test-agent",
    daemon: bool = False,
    escalation_targets: list[str] | None = None,
) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        purpose="test",
        tools_allowed=[],
        daemon=daemon,
        escalation_targets=escalation_targets or [],
    )


async def _drain(bus: SqliteMessageBus, recipient: str, max_n: int = 10) -> list[Any]:
    """Collect all pending messages for a recipient."""
    msgs = []
    for _ in range(max_n):
        m = await bus.receive(recipient, timeout=0.05)
        if m is None:
            break
        msgs.append(m)
    return msgs


# ── MemoryAgent ────────────────────────────────────────────────────


class TestMemoryAgent:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_uid())
        yield b
        await b.close()

    @pytest.fixture
    def mock_manager(self):
        m = MagicMock()
        m.store = AsyncMock(return_value="fact-uuid-1")
        m.assemble_context = AsyncMock(return_value={"episodes": [], "semantic": []})
        return m

    def _agent(self, bus, manager):
        return MemoryAgent(_manifest("mem-1"), bus, MagicMock(), manager)

    @pytest.mark.asyncio
    async def test_store_op(self, bus, mock_manager):
        agent = self._agent(bus, mock_manager)
        await bus.send(
            new_message(
                "caller",
                "mem-1",
                MessageKind.TASK_REQUEST,
                {"op": "store", "content": "hello", "project_id": "proj-A"},
            )
        )
        await bus.send(new_message("caller", "mem-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any(r.payload.get("op") == "store" for r in replies)
        mock_manager.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_op(self, bus, mock_manager):
        agent = self._agent(bus, mock_manager)
        await bus.send(
            new_message(
                "caller",
                "mem-1",
                MessageKind.TASK_REQUEST,
                {"op": "context", "query": "what is CORTEX?", "project_id": "proj-A"},
            )
        )
        await bus.send(new_message("caller", "mem-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any(r.payload.get("op") == "context" for r in replies)
        mock_manager.assemble_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_op(self, bus, mock_manager):
        agent = self._agent(bus, mock_manager)
        await bus.send(new_message("caller", "mem-1", MessageKind.TASK_REQUEST, {"op": "status"}))
        await bus.send(new_message("caller", "mem-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        task_results = [r for r in replies if r.kind == MessageKind.TASK_RESULT]
        assert any(r.payload.get("result", {}).get("status") == "ok" for r in task_results)

    @pytest.mark.asyncio
    async def test_unknown_op(self, bus, mock_manager):
        agent = self._agent(bus, mock_manager)
        await bus.send(new_message("caller", "mem-1", MessageKind.TASK_REQUEST, {"op": "nuke"}))
        await bus.send(new_message("caller", "mem-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any("error" in r.payload for r in replies)

    @pytest.mark.asyncio
    async def test_store_error_reply(self, bus, mock_manager):
        mock_manager.store.side_effect = RuntimeError("db locked")
        agent = self._agent(bus, mock_manager)
        await bus.send(
            new_message(
                "caller",
                "mem-1",
                MessageKind.TASK_REQUEST,
                {"op": "store", "content": "x"},
            )
        )
        await bus.send(new_message("caller", "mem-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any("error" in r.payload for r in replies)

    @pytest.mark.asyncio
    async def test_non_task_request_ignored(self, bus, mock_manager):
        agent = self._agent(bus, mock_manager)
        await bus.send(new_message("caller", "mem-1", MessageKind.HEARTBEAT, {}))
        await bus.send(new_message("caller", "mem-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        # No TASK_RESULT should be emitted for HEARTBEAT
        replies = await _drain(bus, "caller")
        assert all(r.kind != MessageKind.TASK_RESULT for r in replies)


# ── VerificationAgent ─────────────────────────────────────────────


class TestVerificationAgent:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_uid())
        yield b
        await b.close()

    @pytest.fixture
    def mock_verifier(self):
        v = MagicMock()
        result = MagicMock()
        result.is_valid = True
        result.violations = []
        result.proof_certificate = "cert-abc"
        result.counterexample = None
        v.check.return_value = result
        return v

    def _agent(self, bus, verifier):
        return VerificationAgent(_manifest("ver-1"), bus, MagicMock(), verifier)

    @pytest.mark.asyncio
    async def test_valid_code(self, bus, mock_verifier):
        agent = self._agent(bus, mock_verifier)
        await bus.send(
            new_message(
                "caller",
                "ver-1",
                MessageKind.TASK_REQUEST,
                {"code": "def foo(): pass", "context": {}},
            )
        )
        await bus.send(new_message("caller", "ver-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        results = [r for r in replies if r.kind == MessageKind.TASK_RESULT]
        assert len(results) == 1
        assert results[0].payload["is_valid"] is True
        assert results[0].payload["violations"] == []

    @pytest.mark.asyncio
    async def test_invalid_code(self, bus, mock_verifier):
        mock_verifier.check.return_value.is_valid = False
        mock_verifier.check.return_value.violations = ["no time.sleep in async"]
        agent = self._agent(bus, mock_verifier)
        await bus.send(
            new_message(
                "caller",
                "ver-1",
                MessageKind.TASK_REQUEST,
                {"code": "time.sleep(1)", "context": {}},
            )
        )
        await bus.send(new_message("caller", "ver-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any(not r.payload.get("is_valid", True) for r in replies if "is_valid" in r.payload)

    @pytest.mark.asyncio
    async def test_missing_code(self, bus, mock_verifier):
        agent = self._agent(bus, mock_verifier)
        await bus.send(
            new_message(
                "caller",
                "ver-1",
                MessageKind.TASK_REQUEST,
                {"context": {}},
            )
        )
        await bus.send(new_message("caller", "ver-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any("error" in r.payload for r in replies)
        mock_verifier.check.assert_not_called()

    @pytest.mark.asyncio
    async def test_verifier_exception_propagated(self, bus, mock_verifier):
        mock_verifier.check.side_effect = ValueError("parse error")
        agent = self._agent(bus, mock_verifier)
        await bus.send(
            new_message(
                "caller",
                "ver-1",
                MessageKind.TASK_REQUEST,
                {"code": "broken", "context": {}},
            )
        )
        await bus.send(new_message("caller", "ver-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any("error" in r.payload for r in replies)


# ── SecurityAgent ─────────────────────────────────────────────────


class TestSecurityAgent:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_uid())
        yield b
        await b.close()

    @pytest.fixture
    def clean_monitor(self):
        m = MagicMock()
        m.check_async = AsyncMock(return_value=[])
        return m

    @pytest.fixture
    def alert_monitor(self):
        m = MagicMock()
        alert = MagicMock()
        alert.severity = "high"
        alert.__str__ = lambda self: "SQL injection detected"
        m.check_async = AsyncMock(return_value=[alert])
        return m

    def _agent(self, bus, monitor, targets=None):
        manifest = _manifest("sec-1", daemon=True, escalation_targets=targets or [])
        return SecurityAgent(manifest, bus, MagicMock(), monitor)

    @pytest.mark.asyncio
    async def test_tick_no_alerts(self, bus, clean_monitor):
        agent = self._agent(bus, clean_monitor, targets=["supervisor"])
        await agent.tick()
        # No ALERT_ENTROPY messages should be emitted
        msgs = await _drain(bus, "supervisor")
        assert msgs == []

    @pytest.mark.asyncio
    async def test_tick_with_alert_broadcasts(self, bus, alert_monitor):
        agent = self._agent(bus, alert_monitor, targets=["supervisor"])
        await agent.tick()

        msgs = await _drain(bus, "supervisor")
        assert len(msgs) == 1
        assert msgs[0].kind == MessageKind.ALERT_ENTROPY
        assert msgs[0].payload["severity"] == "high"
        assert msgs[0].payload["source"] == "security_monitor"

    @pytest.mark.asyncio
    async def test_tick_no_targets_suppresses_broadcast(self, bus, alert_monitor):
        agent = self._agent(bus, alert_monitor, targets=[])
        await agent.tick()
        # No crash — warning logged, no message sent

    @pytest.mark.asyncio
    async def test_on_demand_scan(self, bus, alert_monitor):
        agent = self._agent(bus, alert_monitor, targets=["supervisor"])
        await bus.send(
            new_message(
                "caller",
                "sec-1",
                MessageKind.TASK_REQUEST,
                {"op": "scan"},
            )
        )
        await bus.send(new_message("caller", "sec-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        msgs = await _drain(bus, "supervisor")
        assert len(msgs) == 1
        assert msgs[0].kind == MessageKind.ALERT_ENTROPY

    @pytest.mark.asyncio
    async def test_monitor_failure_raises(self, bus):
        bad_monitor = MagicMock()
        bad_monitor.check_async = AsyncMock(side_effect=OSError("disk error"))
        agent = self._agent(bus, bad_monitor)

        with pytest.raises(RuntimeError, match="SecurityMonitor failure"):
            await agent.tick()


# ── HandoffAgent ──────────────────────────────────────────────────


class TestHandoffAgent:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_uid())
        yield b
        await b.close()

    def _agent(self, bus, tmp_path):
        return HandoffAgent(_manifest("hand-1"), bus, MagicMock(), handoff_dir=tmp_path)

    @pytest.mark.asyncio
    async def test_save_handoff_request(self, bus, tmp_path):
        agent = self._agent(bus, tmp_path)
        await bus.send(
            new_message(
                "caller",
                "hand-1",
                MessageKind.HANDOFF_REQUEST,
                {"handoff": {"session": "abc", "context": {"facts": ["f1"]}}},
            )
        )
        await bus.send(new_message("caller", "hand-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        accepted = [r for r in replies if r.kind == MessageKind.HANDOFF_ACCEPTED]
        assert len(accepted) == 1
        assert accepted[0].payload["saved"] is True

    @pytest.mark.asyncio
    async def test_save_handoff_missing_key(self, bus, tmp_path):
        agent = self._agent(bus, tmp_path)
        await bus.send(
            new_message(
                "caller",
                "hand-1",
                MessageKind.HANDOFF_REQUEST,
                {},  # no 'handoff' key
            )
        )
        await bus.send(new_message("caller", "hand-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any("error" in r.payload for r in replies)

    @pytest.mark.asyncio
    async def test_unknown_task_op(self, bus, tmp_path):
        agent = self._agent(bus, tmp_path)
        await bus.send(
            new_message(
                "caller",
                "hand-1",
                MessageKind.TASK_REQUEST,
                {"op": "nuke"},
            )
        )
        await bus.send(new_message("caller", "hand-1", MessageKind.SHUTDOWN, {}))
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any("error" in r.payload for r in replies)


# ── NightshiftAgent ───────────────────────────────────────────────


class TestNightshiftAgent:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_uid())
        yield b
        await b.close()

    @pytest.fixture
    def mock_daemon(self):
        d = MagicMock()
        d.run_cycle = AsyncMock(return_value={"crystals": ["c1", "c2"], "duration_s": 1.2})
        d.stop = MagicMock()
        return d

    def _agent(self, bus, daemon, targets=None):
        manifest = _manifest("night-1", daemon=True, escalation_targets=targets or [])
        return NightshiftAgent(manifest, bus, MagicMock(), daemon)

    @pytest.mark.asyncio
    async def test_tick_emits_fact_proposals(self, bus, mock_daemon):
        agent = self._agent(bus, mock_daemon)
        await agent.tick()

        proposals = await _drain(bus, "memory_agent")
        assert len(proposals) == 2
        assert all(p.kind == MessageKind.FACT_PROPOSAL for p in proposals)
        assert all(p.payload["source"] == "nightshift" for p in proposals)

    @pytest.mark.asyncio
    async def test_tick_no_crystals(self, bus, mock_daemon):
        mock_daemon.run_cycle.return_value = {"crystals": [], "duration_s": 0.1}
        agent = self._agent(bus, mock_daemon)
        await agent.tick()

        proposals = await _drain(bus, "memory_agent")
        assert proposals == []

    @pytest.mark.asyncio
    async def test_tick_publishes_summary_to_targets(self, bus, mock_daemon):
        agent = self._agent(bus, mock_daemon, targets=["supervisor"])
        await agent.tick()

        summaries = await _drain(bus, "supervisor")
        assert len(summaries) == 1
        assert "cycle_report" in summaries[0].payload
        assert summaries[0].payload["cycle_report"]["duration_s"] == 1.2

    @pytest.mark.asyncio
    async def test_shutdown_message_stops_daemon(self, bus, mock_daemon):
        """BaseAgent intercepts SHUTDOWN before handle_message is called.
        Test the handler directly to validate daemon.stop() is invoked."""
        agent = self._agent(bus, mock_daemon)
        shutdown_msg = new_message("supervisor", "night-1", MessageKind.SHUTDOWN, {})
        await agent.handle_message(shutdown_msg)
        mock_daemon.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_cycle_failure_raises(self, bus, mock_daemon):
        mock_daemon.run_cycle.side_effect = RuntimeError("connection lost")
        agent = self._agent(bus, mock_daemon)
        with pytest.raises(RuntimeError, match="NightShiftCrystalDaemon failure"):
            await agent.tick()


# ── SupervisorAgent ───────────────────────────────────────────────


class TestSupervisorAgent:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_uid())
        yield b
        await b.close()

    @pytest.fixture
    def mock_supervisor(self):
        s = MagicMock(spec=Supervisor)
        s.start_agent = AsyncMock()
        s.stop_agent = AsyncMock()
        s.quarantine_agent = AsyncMock()
        s.health_check = AsyncMock()
        s.status = MagicMock(return_value={"agent-x": {"status": "idle"}})
        return s

    def _agent(self, bus, supervisor):
        return SupervisorAgent(_manifest("sup-1"), bus, MagicMock(), supervisor)

    async def _req(self, bus, op: str, extra: dict | None = None) -> None:
        payload = {"op": op, **(extra or {})}
        await bus.send(new_message("caller", "sup-1", MessageKind.TASK_REQUEST, payload))
        await bus.send(new_message("caller", "sup-1", MessageKind.SHUTDOWN, {}))

    @pytest.mark.asyncio
    async def test_status_op(self, bus, mock_supervisor):
        agent = self._agent(bus, mock_supervisor)
        await self._req(bus, "status")
        await agent.run()

        replies = await _drain(bus, "caller")
        results = [r for r in replies if r.kind == MessageKind.TASK_RESULT]
        assert any("result" in r.payload for r in results)
        mock_supervisor.status.assert_called()

    @pytest.mark.asyncio
    async def test_start_op(self, bus, mock_supervisor):
        agent = self._agent(bus, mock_supervisor)
        await self._req(bus, "start", {"agent_id": "agent-x"})
        await agent.run()

        mock_supervisor.start_agent.assert_called_once_with("agent-x")
        replies = await _drain(bus, "caller")
        assert any(r.payload.get("result", {}).get("started") == "agent-x" for r in replies)

    @pytest.mark.asyncio
    async def test_stop_op(self, bus, mock_supervisor):
        agent = self._agent(bus, mock_supervisor)
        await self._req(bus, "stop", {"agent_id": "agent-x"})
        await agent.run()

        mock_supervisor.stop_agent.assert_called_once_with("agent-x")
        replies = await _drain(bus, "caller")
        assert any(r.payload.get("result", {}).get("stopped") == "agent-x" for r in replies)

    @pytest.mark.asyncio
    async def test_quarantine_op(self, bus, mock_supervisor):
        agent = self._agent(bus, mock_supervisor)
        await self._req(bus, "quarantine", {"agent_id": "agent-x"})
        await agent.run()

        mock_supervisor.quarantine_agent.assert_called_once_with("agent-x")
        replies = await _drain(bus, "caller")
        assert any(r.payload.get("result", {}).get("quarantined") == "agent-x" for r in replies)

    @pytest.mark.asyncio
    async def test_start_missing_agent_id(self, bus, mock_supervisor):
        agent = self._agent(bus, mock_supervisor)
        await self._req(bus, "start")  # no agent_id
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any("error" in r.payload for r in replies)
        mock_supervisor.start_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_op(self, bus, mock_supervisor):
        agent = self._agent(bus, mock_supervisor)
        await self._req(bus, "nuke")
        await agent.run()

        replies = await _drain(bus, "caller")
        assert any("error" in r.payload for r in replies)

    @pytest.mark.asyncio
    async def test_health_op(self, bus, mock_supervisor):
        agent = self._agent(bus, mock_supervisor)
        await self._req(bus, "health")
        await agent.run()

        mock_supervisor.health_check.assert_called()
        mock_supervisor.status.assert_called()
