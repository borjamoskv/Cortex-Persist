# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging

from babylon60.sica.strategy import SearchStrategy

from .types import TournamentResult

logger = logging.getLogger("cortex.sica.colony.tournament")


class Tournament:
    """Competitive evaluation of genomes.

    Agents submit their genomes, which are evaluated against
    a shared benchmark. The winner's genome fragments get
    promoted in the gene pool.
    """

    def __init__(self) -> None:
        self._results_history: list[TournamentResult] = []

    @property
    def history(self) -> list[TournamentResult]:
        return list(self._results_history)

    def compete(
        self,
        entries: dict[str, SearchStrategy],
    ) -> TournamentResult:
        """Run a tournament between agent strategies.

        Evaluation criteria:
        1. Current fitness (40%)
        2. Genome diversity / heuristic count (20%)
        3. Exploration-exploitation balance (20%)
        4. Mutation efficiency (20%)
        """
        scores: list[tuple[str, float]] = []

        for agent_id, strategy in entries.items():
            genome = strategy.genome
            fitness_score = strategy.current_fitness * 0.4

            # Diversity: number of active heuristics (more = better, up to a point)
            n_active = len(genome.active_heuristics)
            diversity_score = min(1.0, n_active / 8) * 0.2

            # Exploration balance: penalize extremes
            er = genome.exploration_rate
            balance_score = (1.0 - abs(er - 0.3) * 2) * 0.2

            # Mutation efficiency: ratio of positive mutations
            mutations = strategy.mutation_log
            if mutations:
                positive = sum(
                    1 for m in mutations if m.fitness_delta is not None and m.fitness_delta > 0
                )
                efficiency = positive / len(mutations)
            else:
                efficiency = 0.5
            efficiency_score = efficiency * 0.2

            total = fitness_score + diversity_score + balance_score + efficiency_score
            scores.append((agent_id, round(total, 4)))

        scores.sort(key=lambda x: x[1], reverse=True)
        winner = scores[0][0]
        winner_score = scores[0][1]
        avg_score = sum(s for _, s in scores) / len(scores)
        selection_pressure = winner_score - avg_score

        result = TournamentResult(
            winner=winner,
            rankings=scores,
            selection_pressure=round(selection_pressure, 4),
        )
        self._results_history.append(result)

        logger.info(
            "Tournament: winner=%s (%.3f), pressure=%.3f",
            winner,
            winner_score,
            selection_pressure,
        )
        return result
