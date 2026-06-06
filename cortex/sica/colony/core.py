# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging
from typing import Any

from cortex.sica.strategy import SearchStrategy

from .genetics import GenePool, GenomeCrossover
from .specialization import SpecializationDetector
from .tournament import Tournament

logger = logging.getLogger("cortex.sica.colony.core")


class Colony:
    """Top-level colony coordinator.

    Manages the gene pool, tournaments, crossover, and
    specialization detection for a group of SICA agents.
    """

    def __init__(self, max_pool_size: int = 100) -> None:
        self.gene_pool = GenePool(max_fragments=max_pool_size)
        self.tournament = Tournament()
        self.crossover = GenomeCrossover()
        self.specialization = SpecializationDetector()
        self._agents: dict[str, SearchStrategy] = {}

    def register(self, agent_id: str, strategy: SearchStrategy) -> None:
        """Register an agent with the colony."""
        self._agents[agent_id] = strategy

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from the colony."""
        self._agents.pop(agent_id, None)

    @property
    def population(self) -> int:
        return len(self._agents)

    def evolve_cycle(self) -> dict[str, Any]:
        """Run one colony evolution cycle:
        1. All agents donate to gene pool
        2. All agents adopt from gene pool
        3. Run tournament
        4. Detect specializations
        5. Top agents breed via crossover

        Returns a report of what happened.
        """
        report: dict[str, Any] = {"cycle": "evolve", "agents": self.population}

        if self.population < 2:
            report["skipped"] = "need >= 2 agents"
            return report

        # 1. Donations
        total_donated = 0
        for agent_id, strategy in self._agents.items():
            donated = self.gene_pool.donate(agent_id, strategy)
            total_donated += len(donated)
        report["donated"] = total_donated

        # 2. Adoptions
        total_adopted = 0
        for agent_id, strategy in self._agents.items():
            adopted = self.gene_pool.adopt(agent_id, strategy)
            total_adopted += len(adopted)
        report["adopted"] = total_adopted

        # 3. Tournament
        result = self.tournament.compete(self._agents)
        report["tournament_winner"] = result.winner
        report["selection_pressure"] = result.selection_pressure

        # 4. Specialization
        specs = self.specialization.detect(self._agents)
        report["specializations"] = {
            k: {"role": v.primary_role, "confidence": v.role_confidence} for k, v in specs.items()
        }

        # 5. Crossover: breed the top 2
        if len(result.rankings) >= 2:
            parent_a_id = result.rankings[0][0]
            parent_b_id = result.rankings[1][0]
            parent_a = self._agents[parent_a_id].genome
            parent_b = self._agents[parent_b_id].genome
            child = self.crossover.crossover(parent_a, parent_b)
            report["crossover"] = {
                "parents": [parent_a_id, parent_b_id],
                "child_hash": child.genome_hash,
                "child_heuristics": len(child.heuristics),
            }
            # Inject child genome into gene pool
            child_strategy = SearchStrategy(child)
            self.gene_pool.donate(
                f"crossover:{parent_a_id}x{parent_b_id}", child_strategy, min_fitness=0.0
            )

        logger.info("Colony evolve cycle: %s", report)
        return report

    def introspect(self) -> dict[str, Any]:
        """Full colony state."""
        return {
            "population": self.population,
            "gene_pool_size": self.gene_pool.size,
            "tournament_count": len(self.tournament.history),
            "agents": list(self._agents.keys()),
            "specializations": {
                k: v.primary_role for k, v in self.specialization.detect(self._agents).items()
            }
            if self.population > 0
            else {},
        }
