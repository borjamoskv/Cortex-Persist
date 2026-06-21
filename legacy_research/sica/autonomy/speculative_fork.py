# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging
import random

from cortex.sica.meta_level import MetaJudgment
from cortex.sica.object_level import ExecutionTrace, StepOutcome
from cortex.sica.strategy import SearchStrategy

logger = logging.getLogger("cortex.sica.autonomy.fork")
from dataclasses import dataclass


@dataclass
class ForkResult:
    """Result of a speculative fork evaluation."""

    fork_id: int
    genome_hash: str
    fitness: float
    mutations_applied: list[str]
    outcome: str  # "adopted" | "discarded"


class SpeculativeFork:
    """Try N parallel strategy mutations and pick the best.

    When the agent hits a hard failure, instead of making a single
    mutation and hoping it works, fork the strategy into N variants,
    evaluate each against recent traces, and adopt the fittest.

    This is the agent's equivalent of "brainstorming multiple approaches
    before committing to one."
    """

    def __init__(self, n_forks: int = 3) -> None:
        self._n_forks = n_forks
        self._fork_history: list[ForkResult] = []

    @property
    def fork_history(self) -> list[ForkResult]:
        return list(self._fork_history)

    def speculate(
        self,
        strategy: SearchStrategy,
        judgment: MetaJudgment,
        recent_traces: list[ExecutionTrace],
    ) -> SearchStrategy:
        """Fork strategy N ways, evaluate, adopt the best.

        Each fork applies a different random mutation.
        Fitness is evaluated by replaying recent traces mentally
        (checking if heuristic weights would have led to better decisions).

        Returns the best forked strategy (or original if no improvement).
        """
        if not judgment.requires_strategy_mutation:
            return strategy

        original_fitness = strategy.current_fitness
        candidates: list[tuple[SearchStrategy, float, list[str]]] = []

        for _i in range(self._n_forks):
            forked = strategy.fork()
            mutations = self._apply_random_mutations(forked, judgment)
            fitness = self._evaluate_fork(forked, recent_traces)
            candidates.append((forked, fitness, mutations))

        # Sort by fitness descending
        candidates.sort(key=lambda c: c[1], reverse=True)
        best_fork, best_fitness, best_mutations = candidates[0]

        # Record all fork results
        for i, (f, fitness, muts) in enumerate(candidates):
            adopted = i == 0 and best_fitness > original_fitness
            self._fork_history.append(
                ForkResult(
                    fork_id=i,
                    genome_hash=f.genome.genome_hash,
                    fitness=round(fitness, 4),
                    mutations_applied=muts,
                    outcome="adopted" if adopted else "discarded",
                )
            )

        if best_fitness > original_fitness:
            logger.info(
                "SpeculativeFork: adopting fork (fitness %.3f → %.3f, mutations=%s)",
                original_fitness,
                best_fitness,
                best_mutations,
            )
            return best_fork
        logger.info(
            "SpeculativeFork: no improvement found (best=%.3f, current=%.3f)",
            best_fitness,
            original_fitness,
        )
        return strategy

    def _apply_random_mutations(
        self,
        strategy: SearchStrategy,
        judgment: MetaJudgment,
    ) -> list[str]:
        """Apply 1-3 random mutations to a forked strategy."""
        mutations_applied: list[str] = []
        n_mutations = random.randint(1, 3)
        genome = strategy.genome

        for _ in range(n_mutations):
            action = random.choice(
                [
                    "amplify_random",
                    "attenuate_random",
                    "adjust_exploration",
                    "swap_tool_priority",
                ]
            )

            if action == "amplify_random" and genome.heuristics:
                h = random.choice(genome.heuristics)
                factor = random.uniform(1.1, 1.5)
                strategy.mutate_amplify(h.name, reason="speculative fork", factor=factor)
                mutations_applied.append(f"amplify:{h.name}")

            elif action == "attenuate_random" and genome.heuristics:
                h = random.choice(genome.heuristics)
                factor = random.uniform(0.4, 0.8)
                strategy.mutate_attenuate(h.name, reason="speculative fork", factor=factor)
                mutations_applied.append(f"attenuate:{h.name}")

            elif action == "adjust_exploration":
                delta = random.uniform(-0.2, 0.2)
                new_rate = max(0.05, min(0.9, genome.exploration_rate + delta))
                strategy.mutate_exploration_rate(new_rate, reason="speculative fork")
                mutations_applied.append(f"exploration:{new_rate:.2f}")

            elif action == "swap_tool_priority" and len(genome.tool_priority) > 1:
                i, j = random.sample(range(len(genome.tool_priority)), 2)
                genome.tool_priority[i], genome.tool_priority[j] = (
                    genome.tool_priority[j],
                    genome.tool_priority[i],
                )
                mutations_applied.append(f"swap_tools:{i}<>{j}")

        return mutations_applied

    def _evaluate_fork(
        self,
        strategy: SearchStrategy,
        recent_traces: list[ExecutionTrace],
    ) -> float:
        """Evaluate a forked strategy against recent trace history.

        Uses a simplified fitness function:
        - Heuristics that were activated on successful traces get bonus
        - Heuristics that were activated on failed traces get penalty
        - Exploration rate is penalized if too extreme
        """
        if not recent_traces:
            return strategy.current_fitness

        score = strategy.current_fitness * 0.5  # Base: intrinsic fitness
        heuristic_names = {h.name for h in strategy.genome.heuristics}

        for trace in recent_traces:
            activated = set(trace.heuristics_activated)
            overlap = activated & heuristic_names

            if trace.final_outcome == StepOutcome.SUCCESS:
                score += 0.1 * len(overlap)  # Reward overlap with success traces
            else:
                score -= 0.05 * len(overlap)  # Penalize overlap with failure traces

        # Penalize extreme exploration rates
        er = strategy.genome.exploration_rate
        if er < 0.1 or er > 0.8:
            score -= 0.1

        return max(0.0, min(1.0, score))
