# [C5-REAL] Exergy-Maximized
"""SICA Strategy - Evolvable Search Heuristics.

A SearchStrategy encodes HOW the agent approaches problem-solving:
  - Tool selection priority
  - Decomposition heuristics
  - Error recovery patterns
  - Exploration vs exploitation balance

Strategies are represented as StrategyGenome - a mutable data structure
that the meta-level can mutate based on performance feedback.

The evolutionary loop:
  1. Execute with current strategy
  2. Meta-level evaluates fitness
  3. Mutate strategy genome
  4. Next execution uses mutated strategy
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex.sica.strategy")


class MutationType(str, Enum):
    """Types of strategy mutations."""

    AMPLIFY = "amplify"  # Strengthen a successful heuristic
    ATTENUATE = "attenuate"  # Weaken a failing heuristic
    SWAP = "swap"  # Replace one heuristic with another
    INJECT = "inject"  # Add a new heuristic
    PRUNE = "prune"  # Remove a dead heuristic
    RECOMBINE = "recombine"  # Merge traits from two strategies


@dataclass
class Heuristic:
    """A single decision heuristic within a strategy.

    Attributes:
        name: Identifier for this heuristic.
        description: Human-readable explanation.
        weight: Influence weight [0.0, 1.0]. Higher = more influence.
        activation_count: Times this heuristic was activated.
        success_count: Times activation led to success.
        last_activated: Monotonic timestamp of last activation.
    """

    name: str
    description: str
    weight: float = 0.5
    activation_count: int = 0
    success_count: int = 0
    last_activated: float = 0.0

    @property
    def fitness(self) -> float:
        """Success rate weighted by recency."""
        if self.activation_count == 0:
            return 0.5  # Prior: neutral
        base_fitness = self.success_count / self.activation_count
        # Recency decay: heuristics not used recently lose fitness
        age = time.monotonic() - self.last_activated if self.last_activated > 0 else 0
        recency_factor = 1.0 / (1.0 + age / 3600)  # Decay over hours
        return base_fitness * 0.7 + recency_factor * 0.3

    def activate(self, success: bool) -> None:
        """Record an activation and its outcome."""
        self.activation_count += 1
        if success:
            self.success_count += 1
        self.last_activated = time.monotonic()


@dataclass
class StrategyGenome:
    """The mutable DNA of a search strategy.

    This is the data structure that the meta-level evolves.
    Each genome encodes:
      - Heuristics with weights
      - Tool priority ordering
      - Decomposition depth preference
      - Error recovery mode
    """

    heuristics: list[Heuristic] = field(default_factory=list)
    tool_priority: list[str] = field(default_factory=list)
    decomposition_depth: int = 3  # Max recursive decomposition
    exploration_rate: float = 0.3  # ε-greedy exploration
    error_recovery_mode: str = (
        "retry_with_mutation"  # retry | escalate | abort | retry_with_mutation
    )
    generation: int = 0
    parent_hash: str = ""

    @property
    def genome_hash(self) -> str:
        """Deterministic hash of the genome state."""
        state = {
            "heuristics": [(h.name, h.weight) for h in self.heuristics],
            "tool_priority": self.tool_priority,
            "decomposition_depth": self.decomposition_depth,
            "exploration_rate": self.exploration_rate,
            "error_recovery_mode": self.error_recovery_mode,
            "generation": self.generation,
        }
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()[:16]

    @property
    def active_heuristics(self) -> list[Heuristic]:
        """Heuristics with weight > threshold."""
        return [h for h in self.heuristics if h.weight > 0.1]

    @property
    def dominant_heuristic(self) -> Heuristic | None:
        """Highest-weight heuristic."""
        if not self.heuristics:
            return None
        return max(self.heuristics, key=lambda h: h.weight)

    def to_dict(self) -> dict[str, Any]:
        return {
            "genome_hash": self.genome_hash,
            "generation": self.generation,
            "parent_hash": self.parent_hash,
            "exploration_rate": self.exploration_rate,
            "decomposition_depth": self.decomposition_depth,
            "error_recovery_mode": self.error_recovery_mode,
            "tool_priority": self.tool_priority,
            "heuristics": [
                {
                    "name": h.name,
                    "weight": round(h.weight, 4),
                    "fitness": round(h.fitness, 4),
                    "activations": h.activation_count,
                    "successes": h.success_count,
                }
                for h in self.heuristics
            ],
        }


# ── Default Strategy Genome ─────────────────────────────────────


def default_genome() -> StrategyGenome:
    """Create the default SICA strategy genome."""
    return StrategyGenome(
        heuristics=[
            Heuristic(
                name="decompose_first",
                description="Break complex problems into sub-tasks before attempting solution.",
                weight=0.8,
            ),
            Heuristic(
                name="verify_before_emit",
                description="Run verification/tests before emitting any result.",
                weight=0.9,
            ),
            Heuristic(
                name="tool_diversity",
                description="Try different tools if the first one fails, don't retry the same tool.",
                weight=0.6,
            ),
            Heuristic(
                name="hypothesis_falsification",
                description="Formulate hypotheses and actively try to falsify them.",
                weight=0.7,
            ),
            Heuristic(
                name="pattern_recognition",
                description="Check if current problem matches a previously solved pattern.",
                weight=0.5,
            ),
            Heuristic(
                name="escalation_threshold",
                description="Escalate to human after 3 consecutive failures on same sub-problem.",
                weight=0.4,
            ),
        ],
        tool_priority=["search", "read", "analyze", "mutate", "verify"],
        decomposition_depth=3,
        exploration_rate=0.3,
        error_recovery_mode="retry_with_mutation",
        generation=0,
    )


@dataclass
class StrategyMutation:
    """Record of a single strategy mutation event.

    Captures what changed, why, and the fitness delta observed.
    """

    mutation_type: MutationType
    target_heuristic: str
    reason: str
    genome_before_hash: str
    genome_after_hash: str
    generation: int
    timestamp: float = field(default_factory=time.monotonic)
    fitness_delta: float | None = None  # Measured after next evaluation

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.mutation_type.value,
            "target": self.target_heuristic,
            "reason": self.reason,
            "before": self.genome_before_hash,
            "after": self.genome_after_hash,
            "generation": self.generation,
            "fitness_delta": self.fitness_delta,
        }


class SearchStrategy:
    """The agent's evolvable search strategy.

    Wraps a StrategyGenome and provides the mutation API
    that the meta-level uses to evolve the strategy.
    """

    def __init__(self, genome: StrategyGenome | None = None) -> None:
        self._genome = genome or default_genome()
        self._mutation_log: list[StrategyMutation] = []
        self._fitness_history: list[tuple[int, float]] = []  # (generation, fitness)

    @property
    def genome(self) -> StrategyGenome:
        return self._genome

    @property
    def mutation_log(self) -> list[StrategyMutation]:
        return list(self._mutation_log)

    @property
    def current_fitness(self) -> float:
        """Aggregate fitness across all active heuristics."""
        active = self._genome.active_heuristics
        if not active:
            return 0.5
        return sum(h.fitness for h in active) / len(active)

    def record_fitness(self) -> None:
        """Snapshot current fitness for tracking."""
        self._fitness_history.append((self._genome.generation, self.current_fitness))

    # ── Mutation API ─────────────────────────────────────────────

    def mutate_amplify(
        self, heuristic_name: str, reason: str, factor: float = 1.3
    ) -> StrategyMutation:
        """Strengthen a heuristic by multiplying its weight."""
        h = self._find_heuristic(heuristic_name)
        before_hash = self._genome.genome_hash

        h.weight = min(1.0, h.weight * factor)
        self._genome.generation += 1
        self._genome.parent_hash = before_hash

        mutation = StrategyMutation(
            mutation_type=MutationType.AMPLIFY,
            target_heuristic=heuristic_name,
            reason=reason,
            genome_before_hash=before_hash,
            genome_after_hash=self._genome.genome_hash,
            generation=self._genome.generation,
        )
        self._mutation_log.append(mutation)
        logger.info(
            "SICA mutation [AMPLIFY] %s: %s (weight=%.3f)", heuristic_name, reason, h.weight
        )
        return mutation

    def mutate_attenuate(
        self, heuristic_name: str, reason: str, factor: float = 0.7
    ) -> StrategyMutation:
        """Weaken a heuristic by reducing its weight."""
        h = self._find_heuristic(heuristic_name)
        before_hash = self._genome.genome_hash

        h.weight = max(0.0, h.weight * factor)
        self._genome.generation += 1
        self._genome.parent_hash = before_hash

        mutation = StrategyMutation(
            mutation_type=MutationType.ATTENUATE,
            target_heuristic=heuristic_name,
            reason=reason,
            genome_before_hash=before_hash,
            genome_after_hash=self._genome.genome_hash,
            generation=self._genome.generation,
        )
        self._mutation_log.append(mutation)
        logger.info(
            "SICA mutation [ATTENUATE] %s: %s (weight=%.3f)", heuristic_name, reason, h.weight
        )
        return mutation

    def mutate_inject(self, heuristic: Heuristic, reason: str) -> StrategyMutation:
        """Inject a new heuristic into the genome."""
        before_hash = self._genome.genome_hash

        self._genome.heuristics.append(heuristic)
        self._genome.generation += 1
        self._genome.parent_hash = before_hash

        mutation = StrategyMutation(
            mutation_type=MutationType.INJECT,
            target_heuristic=heuristic.name,
            reason=reason,
            genome_before_hash=before_hash,
            genome_after_hash=self._genome.genome_hash,
            generation=self._genome.generation,
        )
        self._mutation_log.append(mutation)
        logger.info("SICA mutation [INJECT] %s: %s", heuristic.name, reason)
        return mutation

    def mutate_prune(self, heuristic_name: str, reason: str) -> StrategyMutation:
        """Remove a dead heuristic from the genome."""
        h = self._find_heuristic(heuristic_name)
        before_hash = self._genome.genome_hash

        self._genome.heuristics.remove(h)
        self._genome.generation += 1
        self._genome.parent_hash = before_hash

        mutation = StrategyMutation(
            mutation_type=MutationType.PRUNE,
            target_heuristic=heuristic_name,
            reason=reason,
            genome_before_hash=before_hash,
            genome_after_hash=self._genome.genome_hash,
            generation=self._genome.generation,
        )
        self._mutation_log.append(mutation)
        logger.info("SICA mutation [PRUNE] %s: %s", heuristic_name, reason)
        return mutation

    def mutate_exploration_rate(self, new_rate: float, reason: str) -> None:
        """Adjust the exploration-exploitation balance."""
        old = self._genome.exploration_rate
        self._genome.exploration_rate = max(0.0, min(1.0, new_rate))
        logger.info(
            "SICA exploration rate: %.2f → %.2f (%s)",
            old,
            self._genome.exploration_rate,
            reason,
        )

    def fork(self) -> SearchStrategy:
        """Create a deep copy for speculative evolution."""
        forked = SearchStrategy(genome=copy.deepcopy(self._genome))
        return forked

    # ── Internals ────────────────────────────────────────────────

    def _find_heuristic(self, name: str) -> Heuristic:
        for h in self._genome.heuristics:
            if h.name == name:
                return h
        raise KeyError(f"Heuristic '{name}' not found in genome")
