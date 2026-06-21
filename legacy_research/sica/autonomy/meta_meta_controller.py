# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from cortex.sica.meta_level import MetaLevel
from cortex.sica.strategy import SearchStrategy


@dataclass
class MetaMetaDiagnosis:
    """Diagnosis of the meta-level's own performance."""

    pattern: str
    severity: str  # "warning" | "critical"
    action_taken: str
    details: str
    timestamp: float = field(default_factory=time.monotonic)


class MetaMetaController:
    """Active self-correction of the meta-level.

    Upgrades _check_meta_patterns from passive logging to active control:
    - Tunnel vision → force diagnosis diversity
    - Stale mutations → reset mutation approach
    - Blind spots → inject diagnostic heuristics
    - Overconfidence → calibrate judgment confidence

    This closes the Nelson-Narens loop recursively:
    the controller monitors the monitor.
    """

    def __init__(self) -> None:
        self._diagnosis_log: list[MetaMetaDiagnosis] = []
        self._intervention_count = 0

    @property
    def diagnosis_log(self) -> list[MetaMetaDiagnosis]:
        return list(self._diagnosis_log)

    def check_and_correct(
        self,
        meta_level: MetaLevel,
        strategy: SearchStrategy,
    ) -> list[MetaMetaDiagnosis]:
        """Run all meta-meta checks and apply corrections.

        Returns list of diagnoses (and actions taken).
        """
        diagnoses: list[MetaMetaDiagnosis] = []

        d = self._check_tunnel_vision(meta_level, strategy)
        if d:
            diagnoses.append(d)

        d = self._check_mutation_stagnation(meta_level, strategy)
        if d:
            diagnoses.append(d)

        d = self._check_judgment_confidence_drift(meta_level)
        if d:
            diagnoses.append(d)

        d = self._check_exploration_convergence(strategy)
        if d:
            diagnoses.append(d)

        self._diagnosis_log.extend(diagnoses)
        return diagnoses

    def _check_tunnel_vision(
        self,
        meta_level: MetaLevel,
        strategy: SearchStrategy,
    ) -> MetaMetaDiagnosis | None:
        """Detect and correct diagnostic tunnel vision.

        If all recent judgments classify the same failure type,
        force the meta-level to consider alternative diagnoses
        by injecting a novelty-seeking heuristic.
        """
        recent = meta_level.judgment_history[-10:]
        if len(recent) < 5:
            return None

        classes = [j.failure_class for j in recent if j.failure_class is not None]
        if not classes or len(set(classes)) > 1:
            return None

        dominant = classes[0]

        # ACTIVE CORRECTION: increase exploration to break out
        old_rate = strategy.genome.exploration_rate
        new_rate = min(0.8, old_rate + 0.2)
        strategy.mutate_exploration_rate(
            new_rate,
            reason=f"Meta-meta: breaking tunnel vision on {dominant.value}",
        )
        self._intervention_count += 1

        return MetaMetaDiagnosis(
            pattern="tunnel_vision",
            severity="warning",
            action_taken=f"exploration_rate {old_rate:.2f}→{new_rate:.2f}",
            details=f"All {len(classes)} recent judgments classified as {dominant.value}",
        )

    def _check_mutation_stagnation(
        self,
        meta_level: MetaLevel,
        strategy: SearchStrategy,
    ) -> MetaMetaDiagnosis | None:
        """Detect and correct mutation stagnation.

        If mutations aren't improving fitness, try a radically
        different approach: reset a random heuristic's weight
        to 0.5 (neutral) to break the local optimum.
        """
        mutations = strategy.mutation_log[-8:]
        if len(mutations) < 5:
            return None

        # Check if all recent mutations had non-positive deltas
        deltas = [m.fitness_delta for m in mutations if m.fitness_delta is not None]
        if not deltas or any(d > 0 for d in deltas):
            return None

        # ACTIVE CORRECTION: reset a random heuristic to neutral
        heuristics = strategy.genome.active_heuristics
        if not heuristics:
            return None

        target = random.choice(heuristics)
        old_weight = target.weight
        target.weight = 0.5
        target.activation_count = 0
        target.success_count = 0
        self._intervention_count += 1

        return MetaMetaDiagnosis(
            pattern="mutation_stagnation",
            severity="critical",
            action_taken=f"reset {target.name} weight {old_weight:.3f}→0.500",
            details=f"Last {len(deltas)} mutations had non-positive fitness delta",
        )

    def _check_judgment_confidence_drift(
        self,
        meta_level: MetaLevel,
    ) -> MetaMetaDiagnosis | None:
        """Detect systematic confidence miscalibration in judgments.

        If the meta-level is consistently overconfident (>0.8) but
        its recommendations don't improve outcomes, flag it.
        """
        recent = meta_level.judgment_history[-15:]
        if len(recent) < 10:
            return None

        high_conf = [j for j in recent if j.confidence > 0.8]
        if len(high_conf) < 7:
            return None

        # Check if high-confidence judgments actually led to improvements
        # (rough proxy: were there meta-failures despite high confidence?)
        meta_fails_with_high_conf = sum(1 for j in high_conf if j.is_meta_failure)

        if meta_fails_with_high_conf >= 3:
            self._intervention_count += 1
            return MetaMetaDiagnosis(
                pattern="confidence_drift",
                severity="warning",
                action_taken="flagged for confidence recalibration",
                details=(
                    f"{meta_fails_with_high_conf}/{len(high_conf)} high-confidence "
                    f"judgments were meta-failures"
                ),
            )
        return None

    def _check_exploration_convergence(
        self,
        strategy: SearchStrategy,
    ) -> MetaMetaDiagnosis | None:
        """Detect premature exploration convergence.

        If exploration rate has been decreasing monotonically and
        is now very low, force a bump to prevent premature convergence.
        """
        genome = strategy.genome
        if genome.exploration_rate > 0.15:
            return None

        # Check if all heuristic weights have converged (low variance)
        weights = [h.weight for h in genome.active_heuristics]
        if not weights or len(weights) < 3:
            return None

        mean_w = sum(weights) / len(weights)
        variance = sum((w - mean_w) ** 2 for w in weights) / len(weights)

        if variance < 0.01:  # Very low diversity
            old_rate = genome.exploration_rate
            new_rate = 0.4  # Force significant exploration
            strategy.mutate_exploration_rate(
                new_rate,
                reason="Meta-meta: breaking premature convergence",
            )
            self._intervention_count += 1

            return MetaMetaDiagnosis(
                pattern="premature_convergence",
                severity="critical",
                action_taken=f"exploration_rate {old_rate:.2f}→{new_rate:.2f}",
                details=f"Weight variance={variance:.4f}, all heuristics converged",
            )
        return None
