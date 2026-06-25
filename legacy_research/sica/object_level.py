# [C5-REAL] Exergy-Maximized
"""SICA Object-Level - Task Execution Engine.

The object-level is WHERE the actual work happens:
  - Receives a task with an objective
  - Applies the current SearchStrategy to decompose and solve
  - Records every step in an ExecutionTrace
  - Reports traces UP to the meta-level for monitoring

The object-level does NOT modify its own strategy. That's the
meta-level's exclusive authority (Nelson-Narens control flow).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from legacy_research.sica.strategy import SearchStrategy

logger = logging.getLogger("cortex.sica.object_level")


class StepOutcome(str, Enum):
    """Outcome of a single execution step."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class ExecutionStep:
    """A single step in the execution trace."""

    step_id: int
    action: str
    tool_used: str | None = None
    heuristic_applied: str | None = None
    input_summary: str = ""
    output_summary: str = ""
    outcome: StepOutcome = StepOutcome.SUCCESS
    error: str | None = None
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.monotonic)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    """Complete execution trace for a single task.

    This is the primary data structure that flows UPWARD to the
    meta-level for monitoring analysis. It contains everything the
    meta-level needs to evaluate strategy fitness.
    """

    task_id: str
    objective: str
    strategy_genome_hash: str
    steps: list[ExecutionStep] = field(default_factory=list)
    final_outcome: StepOutcome = StepOutcome.SUCCESS
    total_duration_ms: float = 0.0
    start_ts: float = field(default_factory=time.monotonic)
    end_ts: float = 0.0

    # Meta-annotations (filled by object-level self-report)
    self_assessed_confidence: float = 0.5
    self_assessed_difficulty: float = 0.5
    error_pattern: str | None = None  # Detected repetitive error pattern

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def success_rate(self) -> float:
        if not self.steps:
            return 0.0
        successes = sum(1 for s in self.steps if s.outcome == StepOutcome.SUCCESS)
        return successes / len(self.steps)

    @property
    def failure_steps(self) -> list[ExecutionStep]:
        return [s for s in self.steps if s.outcome == StepOutcome.FAILURE]

    @property
    def tools_used(self) -> list[str]:
        return list({s.tool_used for s in self.steps if s.tool_used})

    @property
    def heuristics_activated(self) -> list[str]:
        return list({s.heuristic_applied for s in self.steps if s.heuristic_applied})

    def add_step(self, step: ExecutionStep) -> None:
        self.steps.append(step)

    def finalize(self, outcome: StepOutcome) -> None:
        """Mark the trace as complete."""
        self.final_outcome = outcome
        self.end_ts = time.monotonic()
        self.total_duration_ms = (self.end_ts - self.start_ts) * 1000

    def detect_error_pattern(self) -> str | None:
        """Detect repetitive error patterns in the trace."""
        if len(self.failure_steps) < 2:
            return None

        pattern = (
            self._check_repeated_tool() or self._check_repeated_error() or self._check_cascade()
        )
        if pattern:
            self.error_pattern = pattern
            return pattern
        return None

    def _check_repeated_tool(self) -> str | None:
        failed_tools = [s.tool_used for s in self.failure_steps if s.tool_used]
        if failed_tools and len(set(failed_tools)) == 1:
            return f"repeated_tool_failure:{failed_tools[0]}"
        return None

    def _check_repeated_error(self) -> str | None:
        errors = [s.error for s in self.failure_steps if s.error]
        if errors and len(set(errors)) == 1:
            return f"repeated_error:{errors[0][:50]}"
        return None

    def _check_cascade(self) -> str | None:
        first_fail_idx = next(
            (i for i, step in enumerate(self.steps) if step.outcome == StepOutcome.FAILURE), None
        )
        if first_fail_idx is not None:
            remaining = self.steps[first_fail_idx:]
            if len(remaining) >= 3 and all(s.outcome == StepOutcome.FAILURE for s in remaining):
                return "cascade_failure"
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "genome_hash": self.strategy_genome_hash,
            "steps": len(self.steps),
            "success_rate": round(self.success_rate, 3),
            "final_outcome": self.final_outcome.value,
            "duration_ms": round(self.total_duration_ms, 1),
            "confidence": self.self_assessed_confidence,
            "difficulty": self.self_assessed_difficulty,
            "error_pattern": self.error_pattern,
            "tools_used": self.tools_used,
            "heuristics_activated": self.heuristics_activated,
        }


class ObjectLevel:
    """The task execution engine.

    Receives objectives, decomposes them using the current strategy,
    executes steps, and produces ExecutionTraces for the meta-level.
    """

    def __init__(self, strategy: SearchStrategy) -> None:
        self._strategy = strategy
        self._current_trace: ExecutionTrace | None = None
        self._trace_archive: list[ExecutionTrace] = []
        self._step_counter = 0

    @property
    def strategy(self) -> SearchStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, new_strategy: SearchStrategy) -> None:
        """Strategy replacement (only via meta-level control)."""
        self._strategy = new_strategy

    @property
    def trace_archive(self) -> list[ExecutionTrace]:
        return list(self._trace_archive)

    @property
    def last_trace(self) -> ExecutionTrace | None:
        return self._trace_archive[-1] if self._trace_archive else None

    def begin_task(self, task_id: str, objective: str) -> ExecutionTrace:
        """Start a new execution trace."""
        self._current_trace = ExecutionTrace(
            task_id=task_id,
            objective=objective,
            strategy_genome_hash=self._strategy.genome.genome_hash,
        )
        self._step_counter = 0
        logger.info(
            "ObjectLevel: BEGIN task=%s genome=%s",
            task_id,
            self._strategy.genome.genome_hash,
        )
        return self._current_trace

    def record_step(
        self,
        action: str,
        outcome: StepOutcome,
        *,
        tool_used: str | None = None,
        heuristic_applied: str | None = None,
        input_summary: str = "",
        output_summary: str = "",
        error: str | None = None,
        duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionStep:
        """Record an execution step in the current trace."""
        if self._current_trace is None:
            raise RuntimeError("No active task. Call begin_task() first.")

        self._step_counter += 1
        step = ExecutionStep(
            step_id=self._step_counter,
            action=action,
            tool_used=tool_used,
            heuristic_applied=heuristic_applied,
            input_summary=input_summary,
            output_summary=output_summary,
            outcome=outcome,
            error=error,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        self._current_trace.add_step(step)

        # Update heuristic activation stats
        if heuristic_applied:
            try:
                h = self._strategy._find_heuristic(heuristic_applied)
                h.activate(success=(outcome == StepOutcome.SUCCESS))
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)
        # Heuristic may have been pruned mid-execution

        return step

    def end_task(self, outcome: StepOutcome, confidence: float = 0.5) -> ExecutionTrace:
        """Finalize the current execution trace and archive it."""
        if self._current_trace is None:
            raise RuntimeError("No active task to end.")

        self._current_trace.self_assessed_confidence = confidence
        self._current_trace.detect_error_pattern()
        self._current_trace.finalize(outcome)

        trace = self._current_trace
        self._trace_archive.append(trace)
        self._current_trace = None

        logger.info(
            "ObjectLevel: END task=%s outcome=%s steps=%d success_rate=%.2f",
            trace.task_id,
            outcome.value,
            trace.step_count,
            trace.success_rate,
        )
        return trace

    def should_decompose(self, difficulty: float) -> bool:
        """Check if decomposition heuristic recommends sub-task creation."""
        genome = self._strategy.genome
        decompose_h = None
        for h in genome.heuristics:
            if h.name == "decompose_first":
                decompose_h = h
                break
        if decompose_h is None or decompose_h.weight < 0.3:
            return False
        return difficulty > (1.0 - decompose_h.weight)

    def should_escalate(self) -> bool:
        """Check if escalation threshold has been reached."""
        if self._current_trace is None:
            return False
        consecutive_failures = 0
        for step in reversed(self._current_trace.steps):
            if step.outcome == StepOutcome.FAILURE:
                consecutive_failures += 1
            else:
                break
        escalation_h = None
        for h in self._strategy.genome.heuristics:
            if h.name == "escalation_threshold":
                escalation_h = h
                break
        threshold = 3 if escalation_h is None else max(1, int(5 * (1 - escalation_h.weight)))
        return consecutive_failures >= threshold
