"""Epistemic Membrane Monitor — autonomous self-healing based on certainty derivative.

Monitors the degradation of epistemic confidence across the knowledge base.
Connects the Metamemory index to the Workflow layer, triggering /autodidact,
/josu, or /immune when entropy reaches critical thresholds (Axiom Ω₂, Ω₁₁).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from cortex.daemon.models import WorkflowAlert
from cortex.daemon.monitors.base import BaseMonitor

__all__ = ["EpistemicMonitor"]

logger = logging.getLogger("moskv-daemon")


class EpistemicMonitor(BaseMonitor[WorkflowAlert]):
    """Monitors the mathematical decay of epistemic certainty.
    """
    Acts as the knowledge immune system. Instead of waiting for time-based
    heuristics, this monitor analyzes the actual confidence derived from the
    Metacognitive Judge and triggers atomic workflows when certainty drops.
    """

    def __init__(
        self,
        engine: Any = None,
        *,
        eval_interval_seconds: int = 600,
        critical_repair_threshold: int = 5,
        decay_velocity_threshold: float = -0.05,
        stale_ratio_threshold: float = 0.20,
    ):
        self._engine = engine
        self._eval_interval_seconds = eval_interval_seconds
        self._critical_repair_threshold = critical_repair_threshold
        # Negative velocity = confidence is dropping
        self._decay_velocity_threshold = decay_velocity_threshold
        self._stale_ratio_threshold = stale_ratio_threshold
        
        self._last_eval: float = 0.0
        self._last_mean_confidence: float | None = None
        self._last_suggestions: list[WorkflowAlert] = []

    def check(self) -> list[WorkflowAlert]:
        """Evaluate epistemic state and trigger self-healing workflows."""
        now = time.monotonic()
        if now - self._last_eval < self._eval_interval_seconds and self._last_suggestions:
            return self._last_suggestions

        suggestions: list[WorkflowAlert] = []

        if not self._engine or not hasattr(self._engine, "memory"):
            return suggestions

        try:
            # Query metamemory stats on the fly
            stats = self._engine.memory.metamemory.summary_stats()
            # 1. Critical Repair Needed -> /josu
            if stats.memories_needing_repair >= self._critical_repair_threshold:
                suggestions.append(
                    WorkflowAlert(
                        workflow="/josu",
                        reason=(
                            f"{stats.memories_needing_repair} memorias en estado crítico. "
                            "Resolución autónoma requerida para evitar colapso."
                        ),
                        confidence="C4🔵",
                        priority=1,
                        tags=["epistemic", "ghosts", "repair"],
                    )
                )

            # 2. Derivative of Certainty (Decay) -> /autodidact
            # If mean confidence is dropping fast, trigger autodidact to re-ingest
            if self._last_mean_confidence is not None:
                velocity = stats.mean_retrieval_confidence - self._last_mean_confidence
                if velocity <= self._decay_velocity_threshold:
                    suggestions.append(
                        WorkflowAlert(
                            workflow="/autodidact",
                            reason=(
                                f"Caída aguda de certeza epistémica (dv/dt = {velocity:.3f}). "
                                "Síntesis y reingesta de conocimiento necesaria."
                            ),
                            confidence="C3🟡",
                            priority=2,
                            tags=["epistemic", "decay", "learning"],
                        )
                    )
            # 3. Staleness Ratio -> /nightshift
            # If > 20% of memory is stale, we need a night cycle to refresh/crystallize
            stale_ratio = 0.0
            if stats.total_memories > 0:
                stale_ratio = stats.stale_memories / stats.total_memories
            
            if stale_ratio >= self._stale_ratio_threshold:
                suggestions.append(
                    WorkflowAlert(
                        workflow="/nightshift",
                        reason=(
                            f"Entropía térmica: {stale_ratio*100:.1f}% de la memoria está obsoleta.\n"
                            "Se requiere cristalización nocturna."
                        ),
                        confidence="C4🔵",
                        priority=3,
                        tags=["epistemic", "stale", "crystallize"],
                    )
                )

            # Update state
            self._last_mean_confidence = stats.mean_retrieval_confidence
            
        except Exception as e:
            logger.error("Failed to evaluate epistemic certainty: %s", e)

        # Sort by priority
        suggestions.sort(key=lambda a: a.priority)

        self._last_eval = now
        self._last_suggestions = suggestions
        return suggestions
