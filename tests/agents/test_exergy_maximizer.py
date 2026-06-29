# [C5-REAL] Exergy-Maximized
"""Tests for CORTEX Level 5 Exergy Maximizer agent (Demiurge)."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import pytest

from cortex.agents.bus import SqliteMessageBus
from cortex.agents.exergy_maximizer import (
    ExergyGradient,
    ExergyMaximizerAgent,
    create_exergy_maximizer,
)
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import MessageKind, new_message
from cortex.agents.planner import StepStatus
from cortex.agents.tools import ToolRegistry


def _unique_db() -> str:
    return f"file:mem_{uuid.uuid4().hex[:8]}?mode=memory&cache=shared"


def _make_manifest(agent_id: str = "test-l5") -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        purpose="Level 5 Agent testing",
        can_delegate=True,
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
    @property
    def name(self) -> str:
        return "error_tool"

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


class TestExergyMaximizerAgent:
    @pytest.fixture
    async def bus(self):
        b = SqliteMessageBus(db_path=_unique_db())
        yield b
        await b.close()

    @pytest.mark.asyncio
    async def test_oom_loop_success(self, bus):
        manifest = _make_manifest("demiurge-test")
        registry = ToolRegistry()
        registry.register(DummyTool("exergy_audit", "optimal"))
        
        agent = ExergyMaximizerAgent(manifest, bus, registry)
        
        result = await agent.execute_objective("Perform diagnostic scan")
        assert result["status"] == "SUCCESS"
        assert result["ooda_final_state"] == "complete"

    @pytest.mark.asyncio
    async def test_replan_on_failure(self, bus):
        manifest = _make_manifest("demiurge-replan")
        registry = ToolRegistry()
        # Initial step uses exergy_audit. Let's make it fail by raising or returning errors.
        # But wait, exergy_audit is built-in. We can register an error tool or override it.
        registry.register(ErrorTool())  # will raise error

        agent = ExergyMaximizerAgent(manifest, bus, registry)
        
        # Override initial plan to use the error tool
        result = await agent.execute_objective("Objective that will fail")
        # Since it fails, OODA State transitions from OBSERVE -> REPLAN -> PERCEIVE -> ACT (noop fallback).
        # noop fallback succeeds and transitions to CRITIQUE -> COMPLETE.
        assert result["status"] == "SUCCESS"
        assert result["ooda_final_state"] == "complete"
        assert "[REPLAN]" in result["plan_summary"]["objective"]

    @pytest.mark.asyncio
    async def test_factory_creation(self, bus):
        agent = create_exergy_maximizer("demiurge-01", bus)
        assert agent.agent_id == "demiurge-01"
        assert agent.manifest.can_delegate is True
        assert agent.manifest.daemon is True
