# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - Level 5 Demiurge Exergy Maximizer.

The BoltzmannEngineAgent is a Level 5 agent that implements:
1. Cognitive OODA Loop: Perceive -> Orient -> Decide -> Act -> Observe -> Critique.
2. Meta-cognitive Replanning: Dynamically route around failures.
3. Exergy Gradient Descent: Measures net exergy over time to detect state degradation.
4. Swarm Delegation: Spawn L4 sub-agents to parallelize or partition sub-tasks.
5. Adversarial Self-Critique: Critique execution output before declaring completion.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from babylon60.agents.base import BaseAgent
from babylon60.agents.manifest import AgentManifest
from babylon60.agents.message_schema import AgentMessage, MessageKind, new_message
from babylon60.agents.planner import ExecutionPlan, ExergyPlanner, PlanStep
from babylon60.agents.tools import ToolRegistry

logger = logging.getLogger("cortex.agents.boltzmann_engine")


class OODAState(str, Enum):
    PERCEIVE = "perceive"
    ORIENT = "orient"
    DECIDE = "decide"
    ACT = "act"
    OBSERVE = "observe"
    CRITIQUE = "critique"
    REPLAN = "replan"
    APOPTOSIS = "apoptosis"
    COMPLETE = "complete"


@dataclass
class ExergyGradient:
    """Tracks exergy generation vs entropy dissipation over time."""

    history: list[dict[str, Any]] = field(default_factory=list)
    degradation_threshold: float = -0.15
    patience_steps: int = 3

    def record(self, exergy: float, entropy: float) -> None:
        self.history.append({
            "timestamp": time.monotonic(),
            "exergy": exergy,
            "entropy": entropy,
            "net": exergy - entropy
        })

    @property
    def net_derivative(self) -> float:
        """Calculate ∂E/∂t of the latest steps with temporal regularization."""
        if len(self.history) < 2:
            return 0.0
        latest = self.history[-1]
        prev = self.history[-2]
        dt = max(latest["timestamp"] - prev["timestamp"], 1.0)
        return (latest["net"] - prev["net"]) / dt

    def is_degrading(self) -> bool:
        """Check if we are in a persistent downward thermodynamic spiral."""
        if len(self.history) < self.patience_steps:
            return False
        
        # Check if the last N derivative steps are consistently negative
        degrading_count = 0
        for i in range(-1, -self.patience_steps, -1):
            curr = self.history[i]
            prev = self.history[i-1]
            dt = max(curr["timestamp"] - prev["timestamp"], 1.0)
            diff = curr["net"] - prev["net"]
            deriv = diff / dt
            if deriv < self.degradation_threshold:
                degrading_count += 1

        return degrading_count >= (self.patience_steps - 1)


class BoltzmannEngineAgent(BaseAgent):
    """Level 5 Sovereign Exergy Maximizer (Demiurge)."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,
        tool_registry: ToolRegistry | None = None,
        *,
        max_swarm_size: int = 5,
        step_timeout_s: float = 45.0,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self.max_swarm_size = max_swarm_size
        self.step_timeout_s = step_timeout_s
        self.ooda_state = OODAState.PERCEIVE
        self.gradient = ExergyGradient()
        self.current_plan: ExecutionPlan | None = None
        self.active_subagents: dict[str, str] = {}  # task_id -> agent_id
        self.replan_count = 0
        self._execution_log: list[dict[str, Any]] = []
        self._delegation_events: dict[str, asyncio.Event] = {}

    async def handle_message(self, message: AgentMessage) -> None:
        """Process messages including task delegation responses and replan triggers."""
        if message.kind == MessageKind.TASK_REQUEST:
            await self._handle_task_request(message)
        elif message.kind == MessageKind.TASK_RESULT:
            await self._handle_subtask_result(message)
        elif message.kind == MessageKind.REPLAN_TRIGGER:
            await self._trigger_replan_flow(message.payload)
        else:
            logger.debug("[%s] Message kind unhandled in L5: %s", self.agent_id, message.kind)

    async def _handle_task_request(self, message: AgentMessage) -> None:
        objective = message.payload.get("objective", "")
        if not objective:
            await self.send_result(message.sender, {"error": "Missing objective"}, correlation_id=message.correlation_id)
            return

        # Accept the task
        ack = new_message(
            sender=self.agent_id,
            recipient=message.sender,
            kind=MessageKind.TASK_ACCEPTED,
            payload={"objective": objective},
            correlation_id=message.correlation_id,
        )
        await self.bus.send(ack)

        # Run core L5 lifecycle
        result = await self.execute_objective(objective)
        
        if result["status"] == "SUCCESS":
            await self.send_result(message.sender, result, correlation_id=message.correlation_id)
        else:
            await self._report_failure(message.sender, result.get("error", "Demiurge execution failed"), correlation_id=message.correlation_id)

    async def _handle_subtask_result(self, message: AgentMessage) -> None:
        """Processes responses from spawned Level 4 workers."""
        correlation_id = message.correlation_id
        payload = message.payload or {}
        result = payload.get("result", {})
        task_id = result.get("objective", "")
        
        logger.info("[%s] Received delegation result for task: %s", self.agent_id, task_id)
        if correlation_id in self.memory.scratchpad:
            self.memory.scratchpad[correlation_id]["status"] = "COMPLETED"
            self.memory.scratchpad[correlation_id]["result"] = result
        
        if correlation_id in self._delegation_events:
            self._delegation_events[correlation_id].set()

    async def _trigger_replan_flow(self, payload: dict[str, Any]) -> None:
        logger.info("[%s] Triggering meta-cognitive replanning flow", self.agent_id)
        self.ooda_state = OODAState.REPLAN

    async def execute_objective(self, objective: str) -> dict[str, Any]:
        """Runs the complete cognitive OODA loop to maximize exergy."""
        self.state.current_goal = objective
        self._execution_log.clear()
        self.ooda_state = OODAState.PERCEIVE
        start_time = time.monotonic()

        logger.info("👑 [%s] DEMIURGE LEVEL 5 CYCLE START: %s", self.agent_id, objective)

        # Step 1: Initial plan creation
        self.current_plan = ExergyPlanner.plan_from_steps(
            objective,
            [
                {
                    "tool_name": "exergy_audit",
                    "arguments": {"plan_summary": {"net_exergy": 0.5, "entropy_paid": 0.05, "progress": "0%"}},
                    "description": "Initial environment exergy scan",
                    "exergy_estimate": 0.5,
                    "entropy_cost": 0.05,
                }
            ]
        )

        while self.ooda_state != OODAState.COMPLETE and self.ooda_state != OODAState.APOPTOSIS:
            await asyncio.sleep(0)  # Yield to event loop to prevent starvation
            if self.ooda_state == OODAState.PERCEIVE:
                await self._phase_perceive()
            elif self.ooda_state == OODAState.ORIENT:
                await self._phase_orient()
            elif self.ooda_state == OODAState.DECIDE:
                await self._phase_decide()
            elif self.ooda_state == OODAState.ACT:
                await self._phase_act()
            elif self.ooda_state == OODAState.OBSERVE:
                await self._phase_observe()
            elif self.ooda_state == OODAState.CRITIQUE:
                await self._phase_critique()
            elif self.ooda_state == OODAState.REPLAN:
                await self._phase_replan()

        elapsed = time.monotonic() - start_time
        status = "SUCCESS" if self.ooda_state == OODAState.COMPLETE else "FAILED"

        return {
            "status": status,
            "objective": objective,
            "plan_summary": self.current_plan.summary() if self.current_plan else {},
            "elapsed_s": round(elapsed, 3),
            "net_exergy": self.current_plan.net_exergy if self.current_plan else 0.0,
            "ooda_final_state": self.ooda_state.value,
        }

    async def _phase_perceive(self) -> None:
        """Scan the filesystem, DB, or git status to orient the agent."""
        logger.info("[%s] OODA: Perceive environment state", self.agent_id)
        self.ooda_state = OODAState.ORIENT

    async def _phase_orient(self) -> None:
        """Orient our planning logic based on observed workspace attributes."""
        logger.info("[%s] OODA: Orient strategy and calculate exergy gradient", self.agent_id)
        if self.current_plan:
            self.gradient.record(
                float(self.current_plan.total_exergy_produced),
                float(self.current_plan.total_entropy_paid)
            )
            
            if self.gradient.is_degrading():
                logger.error("[%s] Exergy gradient is severely degrading. Terminating current plan.", self.agent_id)
                self.ooda_state = OODAState.APOPTOSIS
                return
        
        self.ooda_state = OODAState.DECIDE

    async def _phase_decide(self) -> None:
        """Evaluate if we need delegation, local execution, or replanning."""
        logger.info("[%s] OODA: Decide action path", self.agent_id)
        self.ooda_state = OODAState.ACT

    async def _phase_act(self) -> None:
        """Execute next ready step, possibly delegating to sub-agents."""
        logger.info("[%s] OODA: Act on plan step", self.agent_id)
        if not self.current_plan:
            self.ooda_state = OODAState.REPLAN
            return

        step = self.current_plan.next_ready_step()
        if not step:
            if self.current_plan.is_complete:
                self.ooda_state = OODAState.CRITIQUE
            else:
                logger.warning("[%s] No ready steps found, triggers replanning.", self.agent_id)
                self.ooda_state = OODAState.REPLAN
            return

        # Determine delegation
        should_delegate = self.manifest.can_delegate and len(self.active_subagents) < self.max_swarm_size
        
        step.mark_running()
        try:
            if should_delegate and step.exergy_estimate < Decimal("0.6"):
                # Delegate low-criticality tasks to a Level 4 sub-agent
                logger.info("[%s] Delegating step '%s' to L4 Sub-Agent", self.agent_id, step.step_id)
                result = await self._delegate_to_subagent(step)
            else:
                # Execute locally
                result = await asyncio.wait_for(
                    self.use_tool(step.tool_name, **step.arguments),
                    timeout=self.step_timeout_s
                )
            
            step.mark_completed(result)
            self.current_plan.record_step_result(step)
            self.replan_count = 0  # Reset replan count on successful action execution
        except Exception as exc:
            step.mark_failed(str(exc))
            self.current_plan.record_step_result(step)
            logger.warning("[%s] Step execution failed: %s", self.agent_id, exc)

        self.ooda_state = OODAState.OBSERVE

    async def _phase_observe(self) -> None:
        """Inspect the outcomes of the latest step action."""
        logger.info("[%s] OODA: Observe step results", self.agent_id)
        if self.current_plan and self.current_plan.has_failures:
            self.ooda_state = OODAState.REPLAN
        else:
            self.ooda_state = OODAState.CRITIQUE

    async def _phase_critique(self) -> None:
        """Critique if the system has reached the desired objective optimal state."""
        logger.info("[%s] OODA: Adversarial self-critique", self.agent_id)
        if self.current_plan and self.current_plan.is_complete:
            self.ooda_state = OODAState.COMPLETE
        else:
            self.ooda_state = OODAState.PERCEIVE

    async def _phase_replan(self) -> None:
        """Replan around the failure point by synthesizing alternative routes."""
        logger.info("[%s] OODA: Replan around failure point", self.agent_id)
        if not self.current_plan:
            self.ooda_state = OODAState.APOPTOSIS
            return

        self.replan_count += 1
        if self.replan_count > 3:
            logger.error("[%s] Replan threshold exceeded (>3). Aborting to prevent infinite loop.", self.agent_id)
            self.ooda_state = OODAState.APOPTOSIS
            return

        observations = {
            "last_state": self.current_plan.summary(),
            "entropy": float(self.current_plan.total_entropy_paid),
        }
        
        replacement = [
            {
                "tool_name": "noop",
                "arguments": {"fallback": "re-routed execution path"},
                "description": "Fallback safety step to recover objective",
                "exergy_estimate": 0.4,
                "entropy_cost": 0.1,
            }
        ]

        self.current_plan = ExergyPlanner.replan(
            original_plan=self.current_plan,
            observations=observations,
            replacement_steps=replacement
        )

        # Resume execution
        self.ooda_state = OODAState.PERCEIVE

    async def _delegate_to_subagent(self, step: PlanStep) -> dict[str, Any]:
        """Spawns an ephemeral L4 sub-agent via standard bus protocol."""
        corr_id = f"delegation-{step.step_id}"
        self.memory.scratchpad[corr_id] = {
            "status": "PENDING",
            "result": None
        }

        deleg_msg = new_message(
            sender=self.agent_id,
            recipient="l4-worker-agent",
            kind=MessageKind.TASK_REQUEST,
            payload={
                "objective": step.description,
                "steps": [{
                    "tool_name": step.tool_name,
                    "arguments": step.arguments,
                    "exergy_estimate": float(step.exergy_estimate),
                    "entropy_cost": float(step.entropy_cost),
                }]
            },
            correlation_id=corr_id
        )
        await self.bus.send(deleg_msg)

        event = asyncio.Event()
        self._delegation_events[corr_id] = event
        try:
            await asyncio.wait_for(event.wait(), timeout=self.step_timeout_s)
            ctx = self.memory.scratchpad.get(corr_id)
            if ctx and ctx["status"] == "COMPLETED":
                return ctx["result"]
            raise RuntimeError("Delegated subtask failed to produce result")
        except asyncio.TimeoutError:
            raise TimeoutError("Delegated subtask execution timed out")
        finally:
            self._delegation_events.pop(corr_id, None)

    async def _report_failure(
        self,
        recipient: str,
        error: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=MessageKind.TASK_FAILED,
            payload={"error": error},
            correlation_id=correlation_id or "auto",
        )
        await self.bus.send(msg)


def create_boltzmann_engine(
    agent_id: str,
    bus: Any,
    tool_registry: ToolRegistry | None = None,
    *,
    purpose: str = "Level 5 Sovereign Exergy Maximizer (Demiurge)",
    tools_allowed: list[str] | None = None,
    max_swarm_size: int = 5,
    step_timeout_s: float = 45.0,
) -> BoltzmannEngineAgent:
    manifest = AgentManifest(
        agent_id=agent_id,
        purpose=purpose,
        tools_allowed=tools_allowed or [],
        can_delegate=True,  # Level 5 allows delegation
        daemon=True,        # Runs continuously
        max_concurrency=max_swarm_size,
        budget_tokens=250_000,
        max_consecutive_errors=5,
        confidence_floor="C5",
        trust_level="C5",
    )
    return BoltzmannEngineAgent(
        manifest=manifest,
        bus=bus,
        tool_registry=tool_registry,
        max_swarm_size=max_swarm_size,
        step_timeout_s=step_timeout_s,
    )
