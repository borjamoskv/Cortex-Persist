# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging
import time
from typing import Any

from cortex.sica.meta_level import MetaLevel
from cortex.sica.object_level import ObjectLevel
from cortex.sica.strategy import SearchStrategy

from .meta_meta_controller import MetaMetaController
from .trace_synthesizer import TraceSynthesizer

logger = logging.getLogger("cortex.sica.autonomy.tick")


class AutonomousTick:
    """Proactive self-diagnostic cycle.

    Runs during idle periods (no messages) to:
    - Prune dead heuristics
    - Synthesize new heuristics from trace history
    - Run meta-meta checks
    - Auto-save genome
    - Adjust exploration rate based on recent performance

    The tick is the agent's "inner monologue" - reflection
    without external stimulus.
    """

    def __init__(
        self,
        min_interval_s: float = 60.0,
        trace_synthesizer: TraceSynthesizer | None = None,
        meta_meta_controller: MetaMetaController | None = None,
    ) -> None:
        self._min_interval = min_interval_s
        self._last_tick: float = 0.0
        self._tick_count: int = 0
        self._synthesizer = trace_synthesizer or TraceSynthesizer()
        self._meta_meta = meta_meta_controller or MetaMetaController()

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def meta_meta(self) -> MetaMetaController:
        return self._meta_meta

    def should_tick(self) -> bool:
        """Check if enough time has elapsed for a diagnostic tick."""
        return (time.monotonic() - self._last_tick) >= self._min_interval

    def execute(
        self,
        strategy: SearchStrategy,
        object_level: ObjectLevel,
        meta_level: MetaLevel,
    ) -> dict[str, Any]:
        """Run the autonomous diagnostic cycle.

        Returns a report of what was done.
        """
        self._last_tick = time.monotonic()
        self._tick_count += 1
        report: dict[str, Any] = {"tick": self._tick_count, "actions": []}

        # 1. Prune dead heuristics
        pruned = self._auto_prune(strategy)
        if pruned:
            report["actions"].append(f"pruned {len(pruned)} dead heuristics: {pruned}")

        # 2. Synthesize new heuristics from traces
        traces = object_level.trace_archive
        new_heuristics = self._synthesizer.synthesize(
            traces,
            strategy.genome.heuristics,
        )
        for h in new_heuristics:
            strategy.mutate_inject(h, reason=f"trace synthesis (tick #{self._tick_count})")
            report["actions"].append(f"synthesized heuristic: {h.name}")

        # 3. Meta-meta self-correction
        diagnoses = self._meta_meta.check_and_correct(meta_level, strategy)
        for d in diagnoses:
            report["actions"].append(f"meta-meta [{d.pattern}]: {d.action_taken}")

        # 4. Exploration rate decay (cool down over time)
        self._cool_exploration(strategy)

        logger.info(
            "AutonomousTick #%d: %d actions",
            self._tick_count,
            len(report["actions"]),
        )
        return report

    def _auto_prune(self, strategy: SearchStrategy) -> list[str]:
        """Prune heuristics with very low fitness and many activations."""
        pruned: list[str] = []
        to_prune = [
            h
            for h in strategy.genome.heuristics
            if h.activation_count > 10 and h.fitness < 0.35 and h.weight < 0.15
        ]
        for h in to_prune:
            strategy.mutate_prune(
                h.name,
                reason=f"auto-prune: fitness={h.fitness:.3f}, activations={h.activation_count}",
            )
            pruned.append(h.name)
        return pruned

    def _cool_exploration(self, strategy: SearchStrategy) -> None:
        """Gradually cool exploration rate toward equilibrium.

        Like simulated annealing: exploration is high early,
        decays toward a baseline as the strategy matures.
        """
        genome = strategy.genome
        generation = genome.generation
        # Target exploration decreases with maturity
        target = max(0.15, 0.5 - (generation * 0.01))
        current = genome.exploration_rate

        if abs(current - target) > 0.05:
            # Move 10% toward target
            new_rate = current + (target - current) * 0.1
            strategy.mutate_exploration_rate(
                new_rate,
                reason=f"cooling (gen={generation}, target={target:.2f})",
            )
