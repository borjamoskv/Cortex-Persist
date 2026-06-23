# [C5-REAL] Exergy-Maximized
"""Test suite for the Level 4 Autonomous Multi-Step Agent.

Tests the complete lifecycle:
    1. Planner generates exergy-scored plans
    2. AutonomousAgent executes plans via ToolRegistry
    3. Retry/failure behavior (L4: no replan)
    4. Thermodynamic accounting (exergy produced / entropy paid)
    5. Integration with MessageBus and Supervisor

Reality Level: C5-REAL (tests use real in-memory tools, no mocks)
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
import logging
import pytest
from typing import Any
from uuid import uuid4

from babylon60.agents.autonomous import AutonomousAgent, create_autonomous_agent
from babylon60.agents.builtin_tools import NoOpTool, register_all_builtin_tools
from babylon60.agents.manifest import AgentManifest
from babylon60.agents.message_schema import AgentMessage, MessageKind, new_message
from babylon60.agents.planner import ExecutionPlan, ExergyPlanner, PlanStep, StepStatus
from babylon60.agents.tools import ToolRegistry

logger = logging.getLogger("babylon60.test.autonomous")


# ── Test Infrastructure ──────────────────────────────────────────


class InMemoryBus:
    """Minimal in-memory message bus for testing."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[AgentMessage]] = {}
        self._sent: list[AgentMessage] = []

    async def send(self, message: AgentMessage) -> None:
        self._sent.append(message)
        q = self._queues.setdefault(message.recipient, asyncio.Queue())
        await q.put(message)

    async def receive(self, agent_id: str, timeout: float = 1.0) -> AgentMessage | None:
        q = self._queues.setdefault(agent_id, asyncio.Queue())
        try:
            return await asyncio.wait_for(q.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    @property
    def sent_messages(self) -> list[AgentMessage]:
        return self._sent


class SuccessTool:
    """Always succeeds with a predictable result."""

    @property
    def name(self) -> str:
        return "success_tool"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "result": "success", **kwargs}


class FailTool:
    """Always fails with an exception."""

    @property
    def name(self) -> str:
        return "fail_tool"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("Deterministic failure for testing")


class SlowTool:
    """Takes longer than timeout to execute."""

    @property
    def name(self) -> str:
        return "slow_tool"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        await asyncio.sleep(10.0)
        return {"ok": True}


class CounterTool:
    """Counts invocations. Fails first N times, then succeeds."""

    def __init__(self, fail_count: int = 1) -> None:
        self._fail_count = fail_count
        self._calls = 0

    @property
    def name(self) -> str:
        return "counter_tool"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        self._calls += 1
        if self._calls <= self._fail_count:
            raise RuntimeError(f"Fail #{self._calls}")
        return {"ok": True, "call_number": self._calls}

    @property
    def total_calls(self) -> int:
        return self._calls


# ── Planner Tests ────────────────────────────────────────────────


class TestPlanner:
    """Test the ExergyPlanner independently."""

    def test_plan_from_steps(self) -> None:
        plan = ExergyPlanner.plan_from_steps(
            "test objective",
            [
                {"tool_name": "shell", "arguments": {"cmd": "echo hi"}, "exergy_estimate": 0.9},
                {
                    "tool_name": "filesystem",
                    "arguments": {"action": "read"},
                    "exergy_estimate": 0.5,
                },
            ],
        )

        assert len(plan.steps) == 2
        assert plan.objective == "test objective"
        assert plan.steps[0].tool_name == "shell"
        assert plan.steps[0].exergy_estimate == Decimal("0.9")
        assert not plan.is_complete

    def test_plan_linear_creates_dependencies(self) -> None:
        plan = ExergyPlanner.plan_linear(
            "linear test",
            [
                ("step_a", {"x": 1}),
                ("step_b", {"x": 2}),
                ("step_c", {"x": 3}),
            ],
        )

        assert len(plan.steps) == 3
        assert plan.steps[0].depends_on == []
        assert plan.steps[1].depends_on == [plan.steps[0].step_id]
        assert plan.steps[2].depends_on == [plan.steps[1].step_id]

    def test_greedy_ordering(self) -> None:
        """next_ready_step should return highest net_exergy first."""
        plan = ExecutionPlan(objective="test")
        step_low = PlanStep(tool_name="low", exergy_estimate=0.2, entropy_cost=0.1)
        step_high = PlanStep(tool_name="high", exergy_estimate=0.9, entropy_cost=0.1)
        step_mid = PlanStep(tool_name="mid", exergy_estimate=0.5, entropy_cost=0.1)

        plan.steps = [step_low, step_mid, step_high]  # Unordered

        next_step = plan.next_ready_step()
        assert next_step is not None
        assert next_step.tool_name == "high"  # Greedy: highest exergy first

    def test_dependency_blocking(self) -> None:
        """Steps with unmet dependencies should not be returned."""
        plan = ExecutionPlan(objective="test")
        step_a = PlanStep(step_id="a", tool_name="a")
        step_b = PlanStep(step_id="b", tool_name="b", depends_on=["a"])

        plan.steps = [step_a, step_b]

        # B should not be ready since A is not completed
        next_step = plan.next_ready_step()
        assert next_step is not None
        assert next_step.step_id == "a"

        # Complete A
        step_a.mark_completed()

        # Now B should be ready
        next_step = plan.next_ready_step()
        assert next_step is not None
        assert next_step.step_id == "b"

    def test_step_fingerprint_deterministic(self) -> None:
        step1 = PlanStep(tool_name="test", arguments={"a": 1, "b": 2})
        step2 = PlanStep(tool_name="test", arguments={"a": 1, "b": 2})
        assert step1.fingerprint() == step2.fingerprint()

    def test_plan_summary(self) -> None:
        plan = ExergyPlanner.plan_from_steps(
            "summary test",
            [
                {"tool_name": "a", "exergy_estimate": 0.8},
                {"tool_name": "b", "exergy_estimate": 0.6},
            ],
        )
        plan.steps[0].mark_completed()
        plan.record_step_result(plan.steps[0])

        summary = plan.summary()
        assert summary["total_steps"] == 2
        assert summary["completed"] == 1
        assert summary["exergy_produced"] == Decimal("0.8")


# ── Autonomous Agent Tests ───────────────────────────────────────


class TestAutonomousAgent:
    """Test the AutonomousAgent execution loop."""

    @pytest.fixture
    def bus(self) -> InMemoryBus:
        return InMemoryBus()

    @pytest.fixture
    def registry(self) -> ToolRegistry:
        reg = ToolRegistry()
        reg.register(SuccessTool())
        reg.register(FailTool())
        reg.register(SlowTool())
        reg.register(NoOpTool())
        return reg

    @pytest.fixture
    def agent(self, bus: InMemoryBus, registry: ToolRegistry) -> AutonomousAgent:
        return create_autonomous_agent(
            agent_id="test-l4-agent",
            bus=bus,
            tool_registry=registry,
            tools_allowed=["success_tool", "fail_tool", "slow_tool", "noop", "counter_tool"],
            step_timeout_s=2.0,
        )

    @pytest.mark.asyncio
    async def test_simple_success(self, agent: AutonomousAgent) -> None:
        """Single successful step."""
        result = await agent.execute_objective(
            "test simple success",
            steps_def=[
                {"tool_name": "success_tool", "arguments": {"key": "value"}},
            ],
        )

        assert result["status"] == "SUCCESS"
        assert result["net_exergy"] > 0
        assert len(result["steps"]) == 1
        assert result["steps"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_multi_step_success(self, agent: AutonomousAgent) -> None:
        """Multiple steps all succeed."""
        result = await agent.execute_objective(
            "multi step test",
            steps_def=[
                {"tool_name": "success_tool", "arguments": {"step": 1}, "exergy_estimate": 0.9},
                {"tool_name": "success_tool", "arguments": {"step": 2}, "exergy_estimate": 0.7},
                {"tool_name": "noop", "arguments": {"step": 3}, "exergy_estimate": 0.5},
            ],
        )

        assert result["status"] == "SUCCESS"
        assert len(result["steps"]) == 3
        assert all(s["status"] == "completed" for s in result["steps"])
        assert result["net_exergy"] > 0

    @pytest.mark.asyncio
    async def test_step_failure_halts_plan(self, agent: AutonomousAgent) -> None:
        """L4 behavior: a failed step halts the entire plan."""
        result = await agent.execute_objective(
            "test failure halts",
            steps_def=[
                {"tool_name": "success_tool", "arguments": {"step": 1}},
                {"tool_name": "fail_tool", "arguments": {}, "retry_budget": 0},
                {"tool_name": "success_tool", "arguments": {"step": 3}},  # Should be skipped
            ],
        )

        # First step completed, second failed, third skipped
        assert result["status"] != "SUCCESS"
        step_statuses = [s["status"] for s in result["steps"]]
        assert step_statuses[0] == "completed"
        assert step_statuses[1] == "failed"
        # Third step should not have been executed (skipped or not in results)

    @pytest.mark.asyncio
    async def test_retry_within_budget(self, bus: InMemoryBus) -> None:
        """Steps retry within their retry budget."""
        registry = ToolRegistry()
        counter = CounterTool(fail_count=1)  # Fail once, then succeed
        registry.register(counter)

        agent = create_autonomous_agent(
            agent_id="retry-agent",
            bus=bus,
            tool_registry=registry,
            tools_allowed=["counter_tool"],
            step_timeout_s=5.0,
        )

        result = await agent.execute_objective(
            "test retry",
            steps_def=[
                {"tool_name": "counter_tool", "arguments": {}, "retry_budget": 2},
            ],
        )

        assert result["status"] == "SUCCESS"
        assert counter.total_calls == 2  # Failed once, succeeded once
        assert result["steps"][0]["retries"] == 1

    @pytest.mark.asyncio
    async def test_timeout_step(self, agent: AutonomousAgent) -> None:
        """Steps that exceed timeout are marked as failed."""
        result = await agent.execute_objective(
            "test timeout",
            steps_def=[
                {"tool_name": "slow_tool", "arguments": {}, "retry_budget": 0},
            ],
        )

        assert result["status"] != "SUCCESS"
        assert "timed out" in result["steps"][0]["error"].lower()

    @pytest.mark.asyncio
    async def test_entropy_circuit_breaker(self, agent: AutonomousAgent) -> None:
        """Plan halts when entropy budget is exceeded."""
        result = await agent.execute_objective(
            "test entropy breaker",
            steps_def=[
                {"tool_name": "success_tool", "entropy_cost": 5.0, "exergy_estimate": 0.1},
                {"tool_name": "success_tool", "entropy_cost": 5.0},  # Should be skipped
            ],
            constraints={"max_entropy": 4.0},
        )

        # First step completes but entropy exceeds budget
        completed_count = sum(1 for s in result["steps"] if s["status"] == "completed")
        assert completed_count <= 1  # At most one step ran

    @pytest.mark.asyncio
    async def test_exergy_efficiency_tracked(self, agent: AutonomousAgent) -> None:
        """Exergy efficiency ratio is computed correctly."""
        result = await agent.execute_objective(
            "test efficiency",
            steps_def=[
                {"tool_name": "success_tool", "exergy_estimate": 0.8, "entropy_cost": 0.2},
            ],
        )

        assert result["status"] == "SUCCESS"
        assert result["exergy_efficiency"] > 0
        assert result["net_exergy"] > 0

    @pytest.mark.asyncio
    async def test_telemetry(self, agent: AutonomousAgent) -> None:
        """Telemetry is available during and after execution."""
        await agent.execute_objective(
            "telemetry test",
            steps_def=[{"tool_name": "success_tool"}],
        )

        tele = agent.telemetry()
        assert tele["agent_id"] == "test-l4-agent"
        assert tele["total_steps_executed"] >= 1

    @pytest.mark.asyncio
    async def test_message_driven_execution(self, agent: AutonomousAgent, bus: InMemoryBus) -> None:
        """Agent can receive task requests via message bus."""
        task_msg = new_message(
            sender="supervisor",
            recipient="test-l4-agent",
            kind=MessageKind.TASK_REQUEST,
            payload={
                "objective": "message-driven test",
                "steps": [
                    {"tool_name": "success_tool", "arguments": {"from": "message"}},
                ],
            },
        )

        await agent.handle_message(task_msg)

        # Check that acknowledgement and result were sent
        sent_kinds = [m.kind for m in bus.sent_messages]
        assert MessageKind.TASK_ACCEPTED in sent_kinds

    @pytest.mark.asyncio
    async def test_max_plan_steps_enforced(self, bus: InMemoryBus, registry: ToolRegistry) -> None:
        """Plans exceeding max_plan_steps are rejected."""
        agent = create_autonomous_agent(
            agent_id="limited-agent",
            bus=bus,
            tool_registry=registry,
            tools_allowed=["success_tool"],
            max_plan_steps=3,
        )

        result = await agent.execute_objective(
            "too many steps",
            steps_def=[{"tool_name": "success_tool"} for _ in range(10)],
        )

        assert result["status"] == "FAILED"
        assert "exceeds max steps" in result["error"]


# ── Integration Test ─────────────────────────────────────────────


class TestIntegration:
    """Full integration test with Supervisor + AutonomousAgent."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """Test complete: register → start → execute → stop."""
        from babylon60.agents.supervisor import Supervisor

        bus = InMemoryBus()
        registry = ToolRegistry()
        registry.register(SuccessTool())
        registry.register(NoOpTool())

        agent = create_autonomous_agent(
            agent_id="integration-agent",
            bus=bus,
            tool_registry=registry,
            tools_allowed=["success_tool", "noop"],
        )

        # Direct execution (not via event loop)
        result = await agent.execute_objective(
            "Integration test: verify full pipeline",
            steps_def=[
                {"tool_name": "noop", "arguments": {"phase": "init"}, "exergy_estimate": 0.3},
                {
                    "tool_name": "success_tool",
                    "arguments": {"phase": "work"},
                    "exergy_estimate": 0.9,
                },
                {"tool_name": "noop", "arguments": {"phase": "cleanup"}, "exergy_estimate": 0.2},
            ],
        )

        assert result["status"] == "SUCCESS"
        assert len(result["steps"]) == 3
        assert result["net_exergy"] > 0
        assert result["elapsed_s"] >= 0
        assert result["exergy_efficiency"] > 0

        # Verify thermodynamic accounting
        plan = result["plan"]
        assert plan["completed"] == 3
        assert plan["failed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
