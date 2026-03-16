"""VEX Planner — Decomposes intent into verifiable execution steps.

The planner is LLM-agnostic: it accepts a decomposition function
that can be backed by any model (Gemini, Claude, GPT, local).

For Phase 1, includes a deterministic planner for known task patterns
(store, search, recall) and a pluggable LLM planner interface.

Derivation: Ω₂ (Entropic Asymmetry) — the plan reduces uncertainty.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Protocol

from cortex.vex.models import PlannedStep, TaskPlan

__all__ = ["Planner", "default_planner"]

logger = logging.getLogger("cortex.vex")


class PlannerBackend(Protocol):
    """Protocol for pluggable LLM planner backends."""

    async def decompose(
        self, intent: str, context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        ...


class Planner:
    """VEX Task Planner — intent → verifiable steps.

    Supports two modes:
    1. Deterministic: Known CORTEX operations (store, search, recall)
    2. LLM-backed: Use a PlannerBackend for arbitrary intent decomposition
    """

    # Known tools that map to CORTEX engine operations.
    _KNOWN_TOOLS: frozenset[str] = frozenset(
        (
            "cortex_store",
            "cortex_search",
            "cortex_recall",
            "cortex_deprecate",
            "cortex_vote",
            "cortex_verify",
            "shell_exec",
            "file_read",
            "file_write",
        )
    )

    def __init__(
        self,
        backend: PlannerBackend | None = None,
        model: str = "",
        source: str = "agent:vex",
    ) -> None:
        self._backend = backend
        self._model = model
        self._source = source

    async def plan(
        self,
        intent: str,
        context: dict[str, Any] | None = None,
    ) -> TaskPlan:
        """Create a TaskPlan from a natural-language intent.

        If a backend is provided, delegates decomposition to the LLM.
        Otherwise, uses deterministic decomposition for known patterns.
        """
        task_id = f"vex_{uuid.uuid4().hex[:12]}"

        if self._backend:
            raw_steps = await self._backend.decompose(intent, context)
            steps = [self._parse_step(s) for s in raw_steps]
        else:
            steps = self._deterministic_plan(intent)

        plan = TaskPlan(
            task_id=task_id,
            intent=intent,
            steps=steps,
            source=self._source,
            model=self._model,
        )

        logger.info(
            "VEX plan created: task_id=%s steps=%d plan_hash=%s",
            plan.task_id,
            len(plan.steps),
            plan.plan_hash[:16],
        )

        return plan

    def _parse_step(self, raw: dict[str, Any]) -> PlannedStep:
        """Parse a raw step dict into a PlannedStep."""
        return PlannedStep(
            step_id=raw.get("step_id", f"step_{uuid.uuid4().hex[:8]}"),
            description=raw.get("description", ""),
            tool=raw.get("tool", "unknown"),
            args=raw.get("args", {}),
            expected_outcome=raw.get("expected_outcome", ""),
            timeout_seconds=raw.get("timeout_seconds", 60),
            tether_check=raw.get("tether_check", True),
            depends_on=raw.get("depends_on", []),
        )

    def _deterministic_plan(self, intent: str) -> list[PlannedStep]:
        """Fallback: single-step plan wrapping the intent as a cortex_store.

        This is the minimal viable plan — stores the intent as a fact
        so that the execution at least has a verifiable record.
        A real deployment would use an LLM backend here.
        """
        return [
            PlannedStep(
                step_id="step_001",
                description=f"Execute intent: {intent[:200]}",
                tool="cortex_store",
                args={
                    "project": "vex",
                    "content": intent,
                    "fact_type": "ghost",
                },
                expected_outcome="Fact stored successfully",
                timeout_seconds=30,
            )
        ]


async def default_planner(
    intent: str,
    model: str = "",
) -> TaskPlan:
    """Convenience function: create a plan with the default planner."""
    planner = Planner(model=model)
    return await planner.plan(intent)
