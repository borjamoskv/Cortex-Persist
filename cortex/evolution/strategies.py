# cortex/evolution/strategies.py
"""Improvement Strategies for the Continuous Improvement Engine.

Phase 2 (v3): All signal-bearing strategies consume real CORTEX telemetry
via CortexMetrics (sync sqlite3, 60s TTL cache):
  - ParameterTuning: delta scales with inverse error_rate
  - PruneDeadPath: threshold from ghost_density
  - BridgeImport: multiplier from bridge_score
  - HeuristicInjection: weights from fact_density

Deliberately stochastic strategies (Adversarial, Entropy, Crossover,
StagnationBreaker) retain controlled randomness by design.

Operator taxonomy (Evolutionary Biology → CORTEX mapping):
    ParameterTuning   — Adaptive mutation rate (Eigen, 1971)
    PruneDeadPath     — Purifying selection (Fisher, 1930)
    HeuristicInjection— Horizontal gene transfer (Ochman et al., 2000)
    BridgeImport      — Symbiotic gene transfer (Margulis, 1970)
    AdversarialStress — Red Queen hypothesis (Van Valen, 1973)
    EntropyReduction  — Genetic drift correction (Kimura, 1968)
    CrossoverRecombi. — Sexual recombination (Maynard Smith, 1978)
    StagnationBreaker — Punctuated equilibrium (Gould & Eldredge, 1972)
"""

from __future__ import annotations

import logging
import secrets
from typing import Protocol

from cortex.evolution.agents import (
    Mutation,
    MutationType,
    SovereignAgent,
    SubAgent,
)
from cortex.evolution.cortex_metrics import CortexMetrics, DomainMetrics

logger = logging.getLogger(__name__)

_rng = secrets.SystemRandom()

# Shared metrics instance — 60s TTL cache, thread-safe
_metrics = CortexMetrics()


def _dm(agent_or_sub: SovereignAgent | SubAgent) -> DomainMetrics:
    """Shorthand to get domain metrics for any entity."""
    return _metrics.get_domain_metrics(agent_or_sub.domain)


class ImprovementStrategy(Protocol):
    """Protocol for pluggable improvement strategies."""

    def evaluate_agent(self, agent: SovereignAgent) -> Mutation | None: ...

    def evaluate_subagent(self, sub: SubAgent) -> Mutation | None: ...


class ParameterTuningStrategy:
    """Adaptive mutation rate — delta scales with error_rate.

    Low errors → small tuning nudges (stable domain).
    High errors → bigger leaps (domain needs aggressive repair).
    """

    def evaluate_agent(self, agent: SovereignAgent) -> Mutation | None:
        m = _dm(agent)
        if m.health_score > 0.9:
            return None  # Already sovereign-grade
        # Scale: error_rate=0 → delta ~ 0.5, error_rate=1 → delta ~ 3.0
        scale = 0.5 + 2.5 * m.error_rate
        delta = scale * _rng.uniform(0.5, 1.2)
        return Mutation(
            mutation_type=MutationType.PARAMETER_TUNE,
            description=(
                f"Tuned {agent.domain.name} params "
                f"(err_rate={m.error_rate:.2f}, health={m.health_score:.2f})"
            ),
            delta_fitness=delta,
        )

    def evaluate_subagent(self, sub: SubAgent) -> Mutation | None:
        m = _dm(sub)
        if m.health_score > 0.9:
            return None
        scale = 0.3 + 1.5 * m.error_rate
        delta = scale * _rng.uniform(0.4, 1.0)
        return Mutation(
            mutation_type=MutationType.PARAMETER_TUNE,
            description=f"Tuned {sub.name} (err={m.error_rate:.2f})",
            delta_fitness=delta,
        )


class PruneDeadPathStrategy:
    """Purifying selection — threshold adjusts with ghost_density.

    More open ghosts → more aggressive pruning (higher threshold).
    """

    def evaluate_agent(self, agent: SovereignAgent) -> Mutation | None:
        m = _dm(agent)
        # ghost_density 0→threshold=20, density 1→threshold=40
        threshold = 20.0 + 20.0 * m.ghost_density
        worst = agent.worst_subagent
        if worst and worst.fitness < threshold:
            return Mutation(
                mutation_type=MutationType.PRUNE_DEAD_PATH,
                description=(
                    f"Pruned dead path in {worst.name} "
                    f"(ghosts={m.ghost_count}, thresh={threshold:.0f})"
                ),
                delta_fitness=1.0 + m.ghost_density * 2.0,
            )
        return None

    def evaluate_subagent(self, sub: SubAgent) -> Mutation | None:
        m = _dm(sub)
        threshold = 15.0 + 10.0 * m.ghost_density
        if sub.fitness < threshold and sub.generation > 5:
            return Mutation(
                mutation_type=MutationType.PRUNE_DEAD_PATH,
                description=f"Reset stagnant {sub.name} (ghosts={m.ghost_count})",
                delta_fitness=10.0,
            )
        return None


class HeuristicInjectionStrategy:
    """Horizontal gene transfer — weights from fact density.

    Richer domains (more facts in CORTEX) get higher multipliers
    because there's more data to inform heuristic decisions.
    """

    _BASE_HEURISTICS: dict[str, float] = {
        "FABRICATION": 0.8,
        "ORCHESTRATION": 0.6,
        "SWARM": 0.7,
        "EVOLUTION": 1.0,
        "SECURITY": 0.9,
        "PERCEPTION": 0.5,
        "MEMORY": 0.7,
        "EXPERIENCE": 0.6,
        "COMMUNICATION": 0.5,
        "VERIFICATION": 0.8,
    }

    def _weight(self, agent: SovereignAgent) -> float:
        m = _dm(agent)
        base = self._BASE_HEURISTICS.get(agent.domain.name, 0.5)
        # fact_density bonus: 0 facts → 0, 100+ facts → +0.5
        density_bonus = min(0.5, m.fact_density / 200.0)
        return base + density_bonus

    def evaluate_agent(self, agent: SovereignAgent) -> Mutation | None:
        if agent.fitness < 80.0:
            w = self._weight(agent)
            delta = w * _rng.uniform(1.0, 3.0)
            return Mutation(
                mutation_type=MutationType.HEURISTIC_INJECT,
                description=f"Injected {agent.domain.name} heuristic (w={w:.2f})",
                delta_fitness=delta,
            )
        return None

    def evaluate_subagent(self, sub: SubAgent) -> Mutation | None:
        if sub.fitness < 60.0:
            m = _dm(sub)
            density_bonus = min(0.3, m.fact_density / 300.0)
            delta = (0.5 + density_bonus) * _rng.uniform(1.0, 2.0)
            return Mutation(
                mutation_type=MutationType.HEURISTIC_INJECT,
                description=f"Injected heuristic into {sub.name}",
                delta_fitness=delta,
            )
        return None


class BridgeImportStrategy:
    """Symbiotic gene transfer — multiplier scales with real bridge count.

    More existing bridges in CORTEX DB → more aggressive knowledge
    transfer, reflecting a culture of proven cross-domain sharing.
    """

    def evaluate_agent(self, agent: SovereignAgent) -> Mutation | None:
        best = agent.best_subagent
        worst = agent.worst_subagent
        if not best or not worst:
            return None
        gap = best.fitness - worst.fitness
        if gap <= 30.0:
            return None
        m = _dm(agent)
        # base_mult=0.1, bridge_score boosts to max 0.25
        mult = 0.1 + 0.15 * m.bridge_score
        delta = gap * mult
        return Mutation(
            mutation_type=MutationType.BRIDGE_IMPORT,
            description=(
                f"Bridge {best.name}→{worst.name} "
                f"(gap={gap:.1f}, mult={mult:.2f}, bridges={m.bridge_count})"
            ),
            delta_fitness=delta,
        )

    def evaluate_subagent(self, _: SubAgent) -> Mutation | None:
        return None  # Bridges happen at agent level


class AdversarialStressStrategy:
    """Red Queen hypothesis — chaos injection.

    If an agent survives stress (fitness > threshold after penalty),
    it gets a resilience bonus. Deliberately stochastic.
    """

    _STRESS_MAGNITUDE: float = 5.0
    _RESILIENCE_BONUS: float = 3.0
    _FRAGILITY_THRESHOLD: float = 100.0

    def evaluate_agent(self, agent: SovereignAgent) -> Mutation | None:
        if agent.fitness < self._FRAGILITY_THRESHOLD:
            return None
        if _rng.random() > 0.3:
            return None
        stress_hit = _rng.uniform(1.0, self._STRESS_MAGNITUDE)
        projected = agent.fitness - stress_hit
        if projected > self._FRAGILITY_THRESHOLD:
            return Mutation(
                mutation_type=MutationType.ADVERSARIAL_STRESS,
                description=(
                    f"Stress PASSED on {agent.domain.name}: "
                    f"−{stress_hit:.1f} absorbed, +{self._RESILIENCE_BONUS:.1f}"
                ),
                delta_fitness=self._RESILIENCE_BONUS,
            )
        return Mutation(
            mutation_type=MutationType.ADVERSARIAL_STRESS,
            description=(
                f"Stress FAILED on {agent.domain.name}: "
                f"projected {projected:.1f} < {self._FRAGILITY_THRESHOLD}"
            ),
            delta_fitness=-1.0,
        )

    def evaluate_subagent(self, sub: SubAgent) -> Mutation | None:
        if sub.fitness < 80.0 or _rng.random() > 0.2:
            return None
        stress = _rng.uniform(0.5, 3.0)
        if (sub.fitness - stress) > 70.0:
            return Mutation(
                mutation_type=MutationType.ADVERSARIAL_STRESS,
                description=f"SubAgent {sub.name} survived stress (−{stress:.1f})",
                delta_fitness=1.5,
            )
        return Mutation(
            mutation_type=MutationType.ADVERSARIAL_STRESS,
            description=f"SubAgent {sub.name} fragile under stress",
            delta_fitness=-0.5,
        )


class EntropyReductionStrategy:
    """Genetic drift correction — Axiom 12 enforcement.

    Compresses mutation history when mutations/gain ratio is too high.
    """

    _MAX_MUTATIONS_PER_GAIN: float = 20.0

    def evaluate_agent(self, agent: SovereignAgent) -> Mutation | None:
        if agent.generation < 10:
            return None
        gain = agent.fitness - 50.0
        if gain <= 0:
            return None
        ratio = agent.generation / gain
        if ratio > self._MAX_MUTATIONS_PER_GAIN:
            return Mutation(
                mutation_type=MutationType.ENTROPY_REDUCTION,
                description=(
                    f"Entropy purge on {agent.domain.name}: "
                    f"{agent.generation} gens for {gain:.0f} gain (ratio={ratio:.1f})"
                ),
                delta_fitness=2.0,
            )
        return None

    def evaluate_subagent(self, sub: SubAgent) -> Mutation | None:
        if sub.generation < 15:
            return None
        gain = sub.fitness - 50.0
        if gain <= 0:
            gain = 1.0
        ratio = sub.generation / gain
        if ratio > self._MAX_MUTATIONS_PER_GAIN:
            return Mutation(
                mutation_type=MutationType.ENTROPY_REDUCTION,
                description=f"Entropy collapse on {sub.name} (ratio={ratio:.1f})",
                delta_fitness=1.5,
            )
        return None


class CrossoverRecombinationStrategy:
    """Sexual recombination — combines traits of best and worst subagents.

    Only triggers when there's enough fitness variance to justify it.
    """

    _MIN_VARIANCE: float = 15.0

    def evaluate_agent(self, agent: SovereignAgent) -> Mutation | None:
        best = agent.best_subagent
        worst = agent.worst_subagent
        if not best or not worst:
            return None
        gap = best.fitness - worst.fitness
        if gap < self._MIN_VARIANCE:
            return None
        delta = gap * 0.4
        return Mutation(
            mutation_type=MutationType.CROSSOVER_RECOMBINE,
            description=(
                f"Crossover in {agent.domain.name}: {best.name}×{worst.name} (gap={gap:.1f})"
            ),
            delta_fitness=min(delta, 5.0),
        )

    def evaluate_subagent(self, sub: SubAgent) -> Mutation | None:
        if sub.fitness < 70.0 and sub.generation > 3:
            m = _dm(sub)
            delta = max(0.5, (70.0 - sub.fitness) * 0.05 * (1.0 + m.health_score))
            return Mutation(
                mutation_type=MutationType.CROSSOVER_RECOMBINE,
                description=f"Population crossover into {sub.name} (h={m.health_score:.2f})",
                delta_fitness=min(2.5, delta),
            )
        return None


class StagnationBreakerStrategy:
    """Punctuated equilibrium — disrupts local optima.

    Uses real fitness_delta from CORTEX metrics + stochastic component.
    """

    _STAGNATION_WINDOW: int = 5

    def _is_stagnated(self, mutations: list[Mutation]) -> bool:
        if len(mutations) < self._STAGNATION_WINDOW:
            return False
        recent = mutations[-self._STAGNATION_WINDOW :]
        return all(abs(m.delta_fitness) < 0.5 for m in recent)

    def evaluate_agent(self, agent: SovereignAgent) -> Mutation | None:
        if not self._is_stagnated(agent.mutations):
            return None
        m = _dm(agent)
        stochastic = _rng.uniform(-1.0, 2.0)
        shock = m.fitness_delta * 1.5 + stochastic
        shock = max(-3.0, min(8.0, shock))
        return Mutation(
            mutation_type=MutationType.STAGNATION_BREAK,
            description=(
                f"Punctuated eq. on {agent.domain.name}: "
                f"shock={shock:+.1f} (delta={m.fitness_delta:+.1f})"
            ),
            delta_fitness=shock,
        )

    def evaluate_subagent(self, sub: SubAgent) -> Mutation | None:
        if not self._is_stagnated(sub.mutations):
            return None
        m = _dm(sub)
        shock = m.fitness_delta + _rng.uniform(-0.5, 1.0)
        shock = max(-2.0, min(6.0, shock))
        return Mutation(
            mutation_type=MutationType.STAGNATION_BREAK,
            description=f"Punctuated eq. on {sub.name}: {shock:+.1f}",
            delta_fitness=shock,
        )


# Default strategy pipeline (order matters — applied sequentially)
# Phase 1: Repair (prune, bridge)
# Phase 2: Grow (heuristics, tuning)
# Phase 3: Stress-test (adversarial)
# Phase 4: Compress (entropy)
# Phase 5: Recombine (crossover)
# Phase 6: Escape plateaus (stagnation break)
DEFAULT_STRATEGIES: list[ImprovementStrategy] = [
    PruneDeadPathStrategy(),
    BridgeImportStrategy(),
    HeuristicInjectionStrategy(),
    ParameterTuningStrategy(),
    AdversarialStressStrategy(),
    EntropyReductionStrategy(),
    CrossoverRecombinationStrategy(),
    StagnationBreakerStrategy(),
]
