# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - Level 4 Autonomous Multi-Step Agent.

The AutonomousAgent is a Level 4 agent that:
    1. Receives an OBJECTIVE via message or direct invocation.
    2. Decomposes it into a plan (via ExergyPlanner).
    3. Executes steps sequentially using tools from the ToolRegistry.
    4. Records thermodynamic telemetry (exergy produced / entropy paid).
    5. Retries failed steps within their retry budget.
    6. Reports results to the supervisor.

    OBJECTIVE ──→ [ PLANNER ] ──→ [ STEP 1 ] ──→ [ STEP 2 ] ──→ ... ──→ RESULT
                                      │               │
                                   [TOOL A]         [TOOL B]

Level 4 Limitation:
    If a step fails beyond its retry budget, the plan HALTS.
    The agent does NOT question its strategy or replan.
    It insists on the original plan - this is by design.
    Meta-cognitive replanning belongs to Level 5+.

Exergy Maximization:
    Every step is scored by its net exergy (work_yield - entropy_cost).
    The planner greedily schedules highest-exergy steps first.
    Failed retries compound entropy_cost, degrading the plan's total
    net exergy - providing a thermodynamic signal of plan quality.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from babylon60.agents.base import BaseAgent
from babylon60.agents.manifest import AgentManifest
from babylon60.agents.message_schema import AgentMessage, MessageKind, new_message
from babylon60.agents.planner import (
    ExecutionPlan,
    ExergyPlanner,
    PlanStep,
    StepStatus,
)
from babylon60.agents.tools import ToolRegistry

logger = logging.getLogger("cortex.agents.autonomous")


class AutonomousAgent(BaseAgent):
    """Level 4 Autonomous Multi-Step Agent - Exergy Maximizer.

    Receives an objective, decomposes into steps, executes tools,
    delivers results. Always maximizes exergy output.

    Architecture:
        ┌──────────────────────────────────────────────┐
        │          AutonomousAgent (L4)                │
        │                                              │
        │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
        │  │ Planner  │→ │ Executor │→ │ Reporter  │  │
        │  │ (DAG)    │  │ (Tools)  │  │ (Metrics) │  │
        │  └──────────┘  └──────────┘  └───────────┘  │
        │                    │                         │
        │               ToolRegistry                   │
        │           (filesystem, http, shell,          │
        │            database, mcp, ...)               │
        └──────────────────────────────────────────────┘
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,
        tool_registry: ToolRegistry | None = None,
        *,
        max_plan_steps: int = 50,
        step_timeout_s: float = 30.0,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._max_plan_steps = max_plan_steps
        self._step_timeout_s = step_timeout_s
        self._current_plan: ExecutionPlan | None = None
        self._execution_log: list[dict[str, Any]] = []

    # ── Message Handling ──────────────────────────────────────────

    async def handle_message(self, message: AgentMessage) -> None:
        """Dispatch incoming messages by kind."""
        if message.kind == MessageKind.TASK_REQUEST:
            await self._handle_task_request(message)
        elif message.kind == MessageKind.TASK_RESULT:
            # Results from delegated subtasks (future L5+ support)
            logger.info("[%s] Received subtask result: %s", self.agent_id, message.payload)
        else:
            logger.debug("[%s] Ignoring message kind: %s", self.agent_id, message.kind)

    async def _handle_task_request(self, message: AgentMessage) -> None:
        """Parse a task request and execute the full plan lifecycle."""
        payload = message.payload
        objective = payload.get("objective", "")
        steps_def = payload.get("steps", [])
        constraints = payload.get("constraints", {})

        if not objective:
            logger.error("[%s] Task request missing 'objective'", self.agent_id)
            await self._report_failure(
                message.sender,
                "Missing objective in task request",
                correlation_id=message.correlation_id,
            )
            return

        # Acknowledge
        ack = new_message(
            sender=self.agent_id,
            recipient=message.sender,
            kind=MessageKind.TASK_ACCEPTED,
            payload={"objective": objective},
            correlation_id=message.correlation_id,
        )
        await self.bus.send(ack)

        # Execute
        result = await self.execute_objective(objective, steps_def, constraints)

        # Report
        if result["status"] == "SUCCESS":
            await self.send_result(
                message.sender,
                result,
                correlation_id=message.correlation_id,
            )
        else:
            await self._report_failure(
                message.sender,
                result.get("error", "Plan execution failed"),
                correlation_id=message.correlation_id,
                details=result,
            )

    # ── Core Execution Loop ───────────────────────────────────────

    async def execute_objective(
        self,
        objective: str,
        steps_def: list[dict[str, Any]] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a complete objective lifecycle.

        This is the main entry point for programmatic invocation.
        Returns a result dict with status, metrics, and step results.

        Reality Level: C5-REAL (all tool invocations produce real results)
        """
        constraints = constraints or {}
        self.state.current_goal = objective
        self._execution_log.clear()
        start_time = time.monotonic()

        logger.info(
            "⚡ [%s] AUTONOMOUS EXECUTION START - Objective: %s",
            self.agent_id,
            objective,
        )

        # ── Phase 1: Plan ──
        if steps_def:
            plan = ExergyPlanner.plan_from_steps(objective, steps_def)
        else:
            # No steps provided - create a single-step plan for the objective itself
            plan = ExergyPlanner.plan_from_steps(
                objective,
                [
                    {
                        "tool_name": "execute_objective",
                        "arguments": {"objective": objective},
                        "description": f"Direct execution of: {objective}",
                        "exergy_estimate": 0.8,
                        "entropy_cost": 0.2,
                    }
                ],
            )

        if len(plan.steps) > self._max_plan_steps:
            return {
                "status": "FAILED",
                "error": f"Plan exceeds max steps ({len(plan.steps)} > {self._max_plan_steps})",
                "plan": plan.summary(),
            }

        self._current_plan = plan

        # Apply constraints
        max_entropy = constraints.get("max_entropy", float("inf"))
        constraints.get("max_retries", None)

        # ── Phase 2: Execute ──
        step_results = []
        while not plan.is_complete:
            step = plan.next_ready_step()
            if step is None:
                # No ready steps and plan not complete = deadlock
                logger.error("[%s] Plan deadlocked - no ready steps", self.agent_id)
                break

            # Execute the step
            step_result = await self._execute_step(step)
            plan.record_step_result(step)
            step_results.append(step_result)

            self._log_step(step, step_result)

            # Entropy circuit breaker
            if plan.total_entropy_paid > max_entropy:
                logger.warning(
                    "[%s] Entropy budget exceeded (%.2f > %.2f) - halting plan",
                    self.agent_id,
                    plan.total_entropy_paid,
                    max_entropy,
                )
                # Mark remaining pending steps as skipped
                for s in plan.steps:
                    if s.status in (StepStatus.PENDING, StepStatus.RETRYING):
                        s.status = StepStatus.SKIPPED
                break

            # If step failed hard, halt (L4 behavior: no replanning)
            if step.status == StepStatus.FAILED:
                logger.error(
                    "[%s] Step '%s' FAILED after %d retries - HALTING PLAN (L4: no replan)",
                    self.agent_id,
                    step.step_id,
                    step.retry_count,
                )
                # Mark remaining steps as skipped
                for s in plan.steps:
                    if s.status in (StepStatus.PENDING, StepStatus.RETRYING):
                        s.status = StepStatus.SKIPPED
                break

            # Emit progress
            await self._emit_progress(plan)

        # ── Phase 3: Report ──
        elapsed = time.monotonic() - start_time
        status = "SUCCESS" if not plan.has_failures else "PARTIAL_FAILURE"
        if all(s.status == StepStatus.FAILED for s in plan.steps):
            status = "TOTAL_FAILURE"

        result = {
            "status": status,
            "objective": objective,
            "plan": plan.summary(),
            "steps": step_results,
            "elapsed_s": round(elapsed, 3),
            "net_exergy": round(plan.net_exergy, 4),
            "exergy_efficiency": round(
                float(plan.total_exergy_produced) / max(float(plan.total_entropy_paid), 0.001), 4
            ),
        }

        logger.info(
            "⚡ [%s] AUTONOMOUS EXECUTION COMPLETE - Status: %s | Net Exergy: %.4f | Elapsed: %.2fs",
            self.agent_id,
            status,
            plan.net_exergy,
            elapsed,
        )

        self.state.current_goal = None
        return result

    # ── Step Execution ────────────────────────────────────────────

    async def _execute_step(self, step: PlanStep) -> dict[str, Any]:
        """Execute a single plan step using the tool registry.

        Retries within the step's retry budget on failure.
        Returns a result dict for telemetry.
        """
        while not step.is_terminal:
            step.mark_running()

            logger.info(
                "[%s] Executing step %s: %s (tool=%s, attempt=%d/%d)",
                self.agent_id,
                step.step_id,
                step.description,
                step.tool_name,
                step.retry_count + 1,
                step.retry_budget + 1,
            )

            try:
                # Invoke tool with timeout
                result = await asyncio.wait_for(
                    self._invoke_tool(step.tool_name, **step.arguments),
                    timeout=self._step_timeout_s,
                )
                step.mark_completed(result)

                logger.info(
                    "[%s] Step %s COMPLETED in %.2fs",
                    self.agent_id,
                    step.step_id,
                    step.elapsed_s or 0,
                )

            except asyncio.TimeoutError:
                error_msg = f"Step timed out after {self._step_timeout_s}s"
                step.mark_failed(error_msg)
                logger.warning("[%s] Step %s TIMEOUT", self.agent_id, step.step_id)

                if step.status == StepStatus.RETRYING:
                    logger.info(
                        "[%s] Step %s retrying (%d/%d)",
                        self.agent_id,
                        step.step_id,
                        step.retry_count,
                        step.retry_budget,
                    )
                    await asyncio.sleep(0.5 * step.retry_count)  # Exponential backoff

            except PermissionError as exc:
                # Tool policy violation - no retry, immediate fail
                step.retry_count = step.retry_budget  # exhaust budget
                step.mark_failed(f"Permission denied: {exc}")
                logger.error("[%s] Step %s PERMISSION DENIED: %s", self.agent_id, step.step_id, exc)

            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                step.mark_failed(error_msg)
                logger.warning(
                    "[%s] Step %s FAILED: %s",
                    self.agent_id,
                    step.step_id,
                    error_msg,
                )

                if step.status == StepStatus.RETRYING:
                    backoff = min(2.0, 0.5 * (2**step.retry_count))
                    logger.info(
                        "[%s] Step %s retrying in %.1fs (%d/%d)",
                        self.agent_id,
                        step.step_id,
                        backoff,
                        step.retry_count,
                        step.retry_budget,
                    )
                    await asyncio.sleep(backoff)

        return {
            "step_id": step.step_id,
            "tool": step.tool_name,
            "description": step.description,
            "status": step.status.value,
            "result": _safe_serialize(step.result),
            "error": step.error,
            "retries": step.retry_count,
            "elapsed_s": round(step.elapsed_s, 3) if step.elapsed_s else None,
            "exergy_estimate": step.exergy_estimate,
            "entropy_cost": step.entropy_cost,
            "fingerprint": step.fingerprint(),
        }

    async def _invoke_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Invoke a tool from the registry with manifest policy enforcement."""
        return await self.use_tool(tool_name, **kwargs)

    # ── Telemetry & Reporting ─────────────────────────────────────

    def _log_step(self, step: PlanStep, result: dict[str, Any]) -> None:
        """Append step result to the execution log."""
        self._execution_log.append(
            {
                "ts": time.monotonic(),
                "step": result,
            }
        )

    async def _emit_progress(self, plan: ExecutionPlan) -> None:
        """Send a progress update to the supervisor."""
        progress_msg = new_message(
            sender=self.agent_id,
            recipient="supervisor",
            kind=MessageKind.TASK_PROGRESS,
            payload={
                "plan_id": plan.plan_id[:8],
                "progress": f"{plan.progress:.0%}",
                "net_exergy": round(plan.net_exergy, 4),
                "completed": sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED),
                "total": len(plan.steps),
            },
        )
        await self.bus.send(progress_msg)

    async def _report_failure(
        self,
        recipient: str,
        error: str,
        *,
        correlation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Report a task failure."""
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=MessageKind.TASK_FAILED,
            payload={
                "error": error,
                "details": details or {},
            },
            correlation_id=correlation_id or "auto",
        )
        await self.bus.send(msg)

    # ── Status ────────────────────────────────────────────────────

    @property
    def current_plan(self) -> ExecutionPlan | None:
        return self._current_plan

    @property
    def execution_log(self) -> list[dict[str, Any]]:
        return list(self._execution_log)

    def telemetry(self) -> dict[str, Any]:
        """Return current agent telemetry."""
        plan_data = self._current_plan.summary() if self._current_plan else None
        return {
            "agent_id": self.agent_id,
            "status": self.state.status.value,
            "current_goal": self.state.current_goal,
            "plan": plan_data,
            "total_steps_executed": len(self._execution_log),
            "errors": self.state.error_count,
        }


def _safe_serialize(obj: Any) -> Any:
    """Best-effort serialization of tool results for logging."""
    if obj is None:
        return None
    if isinstance(obj, str | int | float | bool):
        return obj
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_safe_serialize(v) for v in obj]
    try:
        return str(obj)[:500]
    except (ValueError, TypeError, OSError, KeyError):
        return "<unserializable>"


def create_autonomous_agent(
    agent_id: str,
    bus: Any,
    tool_registry: ToolRegistry | None = None,
    *,
    purpose: str = "Autonomous multi-step executor with exergy maximization",
    tools_allowed: list[str] | None = None,
    max_plan_steps: int = 50,
    step_timeout_s: float = 30.0,
    budget_tokens: int = 100_000,
    max_consecutive_errors: int = 5,
) -> AutonomousAgent:
    """Factory function to create a fully configured AutonomousAgent.

    Usage:
        agent = create_autonomous_agent(
            agent_id="bounty-hunter-01",
            bus=message_bus,
            tool_registry=registry,
            tools_allowed=["filesystem", "http", "shell", "database"],
        )

        result = await agent.execute_objective(
            "Clone repo, run tests, fix failures, open PR",
            steps_def=[
                {"tool_name": "shell", "arguments": {"cmd": "git clone ..."}, "exergy_estimate": 0.9},
                {"tool_name": "shell", "arguments": {"cmd": "pytest"}, "exergy_estimate": 0.8},
                {"tool_name": "filesystem", "arguments": {"action": "edit", ...}, "exergy_estimate": 0.7},
                {"tool_name": "shell", "arguments": {"cmd": "git push ..."}, "exergy_estimate": 0.6},
            ]
        )
    """
    manifest = AgentManifest(
        agent_id=agent_id,
        purpose=purpose,
        tools_allowed=tools_allowed or [],
        can_delegate=False,  # L4: no delegation
        daemon=False,
        max_concurrency=1,
        budget_tokens=budget_tokens,
        max_consecutive_errors=max_consecutive_errors,
        confidence_floor="C4",
        trust_level="C4",
    )

    return AutonomousAgent(
        manifest=manifest,
        bus=bus,
        tool_registry=tool_registry,
        max_plan_steps=max_plan_steps,
        step_timeout_s=step_timeout_s,
    )
