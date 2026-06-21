# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - Exergy-Aware Planner.

Decomposes an objective into an ordered sequence of executable steps.
Each step is annotated with:
    - tool_name: which tool to invoke
    - arguments: kwargs for the tool
    - exergy_estimate: predicted work-potential (0.0–1.0)
    - retry_budget: max retries before step is declared dead

The planner uses greedy thermodynamic ordering: steps with highest
estimated exergy output are scheduled first (Structure × Information
yield per unit of Entropy paid).

This is a Level 4 planner: it generates plans but does NOT question
its own strategy mid-execution. If a step fails beyond retry budget,
the plan halts - no meta-cognitive replanning.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("cortex.agents.planner")


class StepStatus(str, Enum):
    """Lifecycle of a single plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class PlanStep:
    """A single atomic step in an execution plan."""

    step_id: str = field(default_factory=lambda: str(uuid4())[:8])
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    # Thermodynamic metadata
    exergy_estimate: Decimal = field(
        default_factory=lambda: Decimal("0.5")
    )  # Expected work yield [0.0, 1.0]
    entropy_cost: Decimal = field(
        default_factory=lambda: Decimal("0.1")
    )  # Expected entropy paid [0.0, 1.0]

    # Execution state
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: str | None = None
    retry_count: int = 0
    retry_budget: int = 2
    started_at: float | None = None
    completed_at: float | None = None

    # Dependencies (step_ids that must complete before this step)
    depends_on: list[str] = field(default_factory=list)

    @property
    def net_exergy(self) -> float:
        """Predicted net exergy: work_yield - entropy_cost."""
        return float(max(Decimal("0.0"), self.exergy_estimate - self.entropy_cost))

    @property
    def elapsed_s(self) -> float | None:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def is_terminal(self) -> bool:
        return self.status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)

    def mark_running(self) -> None:
        self.status = StepStatus.RUNNING
        self.started_at = time.monotonic()

    def mark_completed(self, result: Any = None) -> None:
        self.status = StepStatus.COMPLETED
        self.result = result
        self.completed_at = time.monotonic()

    def mark_failed(self, error: str) -> None:
        self.error = error
        if self.retry_count < self.retry_budget:
            self.status = StepStatus.RETRYING
            self.retry_count += 1
        else:
            self.status = StepStatus.FAILED
            self.completed_at = time.monotonic()

    def fingerprint(self) -> str:
        """SHA-256 fingerprint of the step configuration (deterministic)."""
        raw = f"{self.tool_name}:{sorted(self.arguments.items())}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class ExecutionPlan:
    """An ordered sequence of PlanSteps with thermodynamic accounting."""

    plan_id: str = field(default_factory=lambda: str(uuid4()))
    objective: str = ""
    steps: list[PlanStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)

    # Aggregate metrics (updated during execution)
    total_exergy_produced: Decimal = field(default_factory=lambda: Decimal("0.0"))
    total_entropy_paid: Decimal = field(default_factory=lambda: Decimal("0.0"))

    @property
    def net_exergy(self) -> float:
        return float(self.total_exergy_produced - self.total_entropy_paid)

    @property
    def is_complete(self) -> bool:
        return all(s.is_terminal for s in self.steps)

    @property
    def has_failures(self) -> bool:
        return any(s.status == StepStatus.FAILED for s in self.steps)

    @property
    def progress(self) -> float:
        if not self.steps:
            return 1.0
        terminal = sum(1 for s in self.steps if s.is_terminal)
        return terminal / len(self.steps)

    def next_ready_step(self) -> PlanStep | None:
        """Return the next step whose dependencies are all completed.

        Among ready steps, prefer the one with highest net_exergy
        (greedy thermodynamic ordering).
        """
        completed_ids = {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}

        candidates = []
        for step in self.steps:
            if step.status in (StepStatus.PENDING, StepStatus.RETRYING):
                deps_met = all(d in completed_ids for d in step.depends_on)
                if deps_met:
                    candidates.append(step)

        if not candidates:
            return None

        # Greedy: highest net exergy first
        candidates.sort(key=lambda s: s.net_exergy, reverse=True)
        return candidates[0]

    def record_step_result(self, step: PlanStep) -> None:
        """Update aggregate thermodynamic accounting after step execution."""
        if step.status == StepStatus.COMPLETED:
            self.total_exergy_produced += step.exergy_estimate
        # Entropy is always paid, even on failure
        self.total_entropy_paid += step.entropy_cost * (1 + step.retry_count)

    def summary(self) -> dict[str, Any]:
        """Produce a signal-dense summary of the plan."""
        return {
            "plan_id": self.plan_id[:8],
            "objective": self.objective,
            "total_steps": len(self.steps),
            "completed": sum(1 for s in self.steps if s.status == StepStatus.COMPLETED),
            "failed": sum(1 for s in self.steps if s.status == StepStatus.FAILED),
            "progress": f"{self.progress:.0%}",
            "net_exergy": round(self.net_exergy, 4),
            "exergy_produced": round(self.total_exergy_produced, 4),
            "entropy_paid": round(self.total_entropy_paid, 4),
        }


class ExergyPlanner:
    """Stateless planner that converts objectives into ExecutionPlans.

    The planner does NOT execute steps - it only generates plans.
    Execution is handled by the AutonomousAgent's run loop.

    Level 4 limitation: the planner generates a single plan upfront.
    If execution fails, it does NOT replan. It retries individual
    steps within their retry budget, then gives up.
    """

    @staticmethod
    def plan_from_steps(
        objective: str,
        steps: list[dict[str, Any]],
    ) -> ExecutionPlan:
        """Create a plan from an explicit list of step definitions.

        Each step dict should have:
            tool_name: str
            arguments: dict (optional)
            description: str (optional)
            exergy_estimate: Decimal (optional, default 0.5)
            entropy_cost: Decimal (optional, default 0.1)
            retry_budget: int (optional, default 2)
            depends_on: list[str] (optional, step_ids)
        """
        plan = ExecutionPlan(objective=objective)

        for i, step_def in enumerate(steps):
            step = PlanStep(
                tool_name=step_def.get("tool_name", f"step_{i}"),
                arguments=step_def.get("arguments", {}),
                description=step_def.get("description", f"Step {i}"),
                exergy_estimate=Decimal(str(step_def.get("exergy_estimate", "0.5"))),
                entropy_cost=Decimal(str(step_def.get("entropy_cost", "0.1"))),
                retry_budget=step_def.get("retry_budget", 2),
                depends_on=step_def.get("depends_on", []),
            )
            plan.steps.append(step)

        logger.info(
            "[PLANNER] Generated plan '%s' with %d steps for: %s",
            plan.plan_id[:8],
            len(plan.steps),
            objective,
        )
        return plan

    @staticmethod
    def plan_linear(
        objective: str,
        tool_sequence: list[tuple[str, dict[str, Any]]],
    ) -> ExecutionPlan:
        """Create a simple linear chain: each step depends on the previous.

        Args:
            objective: High-level goal description.
            tool_sequence: List of (tool_name, arguments) tuples.
        """
        plan = ExecutionPlan(objective=objective)
        prev_id: str | None = None

        for i, (tool_name, args) in enumerate(tool_sequence):
            step = PlanStep(
                tool_name=tool_name,
                arguments=args,
                description=f"[{i}] {tool_name}",
                depends_on=[prev_id] if prev_id else [],
            )
            plan.steps.append(step)
            prev_id = step.step_id

        return plan
