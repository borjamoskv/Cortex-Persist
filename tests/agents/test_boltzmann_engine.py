# [C5-REAL] Exergy-Maximized
"""Tests for CORTEX Level 5 Exergy Maximizer agent (Demiurge)."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import pytest

from cortex.agents.bus import SqliteMessageBus
from cortex.agents.boltzmann_engine import (
    ExergyGradient,
    BoltzmannEngineAgent,
    create_boltzmann_engine,
)
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import MessageKind, new_message
from cortex.agents.planner import StepStatus
from cortex.agents.tools import ToolRegistry


def _unique_db() -> str:
    return f"file:mem_{uuid.uuid4().hex[:8]}?mode=memory&cache=shared"


def _make_manifest(agent_id: str = "test-l5", can_delegate: bool = False) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        purpose="Level 5 Agent testing",
        can_delegate=can_delegate,
        daemon=True,
    )


class DummyTool:
    def __init__(self, name: str = "noop", result: str = "ok"):
        self._name = name
        self._result = result

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, **kwargs) -> str:
        return self._result


class ErrorTool:
    def __init__(self, name: str = "error_tool"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, **kwargs) -> str:
        raise RuntimeError("Local execution error")


class TestExergyGradient:
    def test_gradient_recording(self):
        grad = ExergyGradient(patience_steps=2)
        grad.record(1.0, 0.1)
        grad.record(1.2, 0.2)
        assert len(grad.history) == 2
        assert grad.net_derivative > 0

    def test_gradient_degradation(self):
        grad = ExergyGradient(patience_steps=2, degradation_threshold=-0.1)
        grad.record(1.0, 0.1)  # net = 0.9
        grad.record(0.5, 0.4)  # net = 0.1
        # dt will be very small, derivative should be highly negative
        assert grad.is_degrading() is True


class TestBoltzmannEngineAgent:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_unique_db())
        yield b
        await b.close()

    @pytest.mark.asyncio
    async def test_oom_loop_success(self, bus):
        manifest = _make_manifest("demiurge-test", can_delegate=False)
        registry = ToolRegistry()
        registry.register(DummyTool("exergy_audit", "optimal"))
        
        agent = BoltzmannEngineAgent(manifest, bus, registry)
        
        result = await agent.execute_objective("Perform diagnostic scan")
        assert result["status"] == "SUCCESS"
        assert result["ooda_final_state"] == "complete"

    @pytest.mark.asyncio
    async def test_replan_on_failure(self, bus):
        manifest = _make_manifest("demiurge-replan", can_delegate=False)
        registry = ToolRegistry()
        registry.register(ErrorTool("exergy_audit"))  # failing step 1
        registry.register(DummyTool("noop", "recovered"))  # successful step 2 (fallback)

        agent = BoltzmannEngineAgent(manifest, bus, registry)
        
        result = await agent.execute_objective("Objective that will fail")
        assert result["status"] == "SUCCESS"
        assert result["ooda_final_state"] == "complete"
        assert "[REPLAN]" in result["plan_summary"]["objective"]

    @pytest.mark.asyncio
    async def test_delegation_flow(self, bus):
        manifest = _make_manifest("demiurge-delegate", can_delegate=True)
        registry = ToolRegistry()
        registry.register(DummyTool("exergy_audit", "optimal"))

        agent = BoltzmannEngineAgent(manifest, bus, registry, step_timeout_s=5.0)

        # Background task that simulates the worker responding to delegation message
        async def simulate_l4_worker():
            await asyncio.sleep(0.5)
            # Find the message sent by the agent to l4-worker-agent
            pending = await bus.receive("l4-worker-agent", timeout=1.0)
            if pending:
                # Reply with task completion message
                reply = new_message(
                    sender="l4-worker-agent",
                    recipient=agent.agent_id,
                    kind=MessageKind.TASK_RESULT,
                    payload={"result": {"objective": pending.payload["objective"], "status": "SUCCESS"}},
                    correlation_id=pending.correlation_id
                )
                await bus.send(reply)
                # Dispatch it to the agent manually so handle_message receives it
                await agent.handle_message(reply)

        worker_task = asyncio.create_task(simulate_l4_worker())
        
        result = await agent.execute_objective("Delegate task")
        assert result["status"] == "SUCCESS"
        assert result["ooda_final_state"] == "complete"
        await worker_task

    @pytest.mark.asyncio
    async def test_factory_creation(self, bus):
        agent = create_boltzmann_engine("demiurge-01", bus)
        assert agent.agent_id == "demiurge-01"
        assert agent.manifest.can_delegate is True
        assert agent.manifest.daemon is True
