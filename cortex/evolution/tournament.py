# cortex/evolution/tournament.py
"""Tournament Selection & Speciation for the Evolution Engine.

Advanced evolutionary operators:
- Tournament: competitive selection between subagents
- Speciation: agents that diverge form new behavioral niches
- Elitism: top performers are protected from regression
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass

from cortex.evolution.agents import (
    Mutation,
    MutationType,
    SovereignAgent,
    SubAgent,
)

logger = logging.getLogger(__name__)
_rng = secrets.SystemRandom()


@dataclass
class TournamentResult:
    """Outcome of a tournament round."""

    winner: SubAgent
    loser: SubAgent
    transferred_fitness: float


def run_tournament(
    agent: SovereignAgent,
    tournament_size: int = 3,
) -> TournamentResult | None:
    """Select `tournament_size` random subagents and compete.

    The winner donates fitness knowledge to the loser.
    Returns None if not enough subagents to form a tournament.
    """
    if len(agent.subagents) < tournament_size:
        return None

    # Sample without replacement
    contestants = _rng.sample(agent.subagents, tournament_size)
    contestants.sort(key=lambda s: s.fitness, reverse=True)

    winner = contestants[0]
    loser = contestants[-1]

    # Knowledge transfer: loser absorbs 15-30% of the gap
    gap = winner.fitness - loser.fitness
    if gap < 2.0:
        return None  # Too close, no meaningful transfer

    transfer = gap * _rng.uniform(0.15, 0.30)
    loser.apply_mutation(
        Mutation(
            mutation_type=MutationType.CROSSOVER_RECOMBINE,
            description=(
                f"Tournament win: {winner.name} → {loser.name} "
                f"(gap={gap:.1f}, transfer={transfer:.1f})"
            ),
            delta_fitness=transfer,
        )
    )

    return TournamentResult(
        winner=winner,
        loser=loser,
        transferred_fitness=transfer,
    )


@dataclass
class Species:
    """A behavioral niche within a domain."""

    name: str
    members: list[SubAgent]
    centroid_fitness: float

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def diversity(self) -> float:
        """Fitness variance within the species."""
        if len(self.members) < 2:
            return 0.0
        mean = sum(s.fitness for s in self.members) / len(self.members)
        variance = sum((s.fitness - mean) ** 2 for s in self.members) / len(self.members)
        return variance**0.5


def speciate(
    agent: SovereignAgent,
    threshold: float = 20.0,
) -> list[Species]:
    """Cluster subagents into species based on fitness distance.

    Uses a simple 1D threshold clustering — subagents within
    `threshold` fitness of each other belong to the same species.
    """
    sorted_subs = sorted(agent.subagents, key=lambda s: s.fitness)
    species_list: list[Species] = []
    current_group: list[SubAgent] = []

    for sub in sorted_subs:
        if not current_group:
            current_group.append(sub)
        elif abs(sub.fitness - current_group[0].fitness) <= threshold:
            current_group.append(sub)
        else:
            centroid = sum(s.fitness for s in current_group) / len(current_group)
            species_list.append(
                Species(
                    name=f"{agent.domain.name}-sp{len(species_list)}",
                    members=current_group,
                    centroid_fitness=centroid,
                )
            )
            current_group = [sub]

    if current_group:
        centroid = sum(s.fitness for s in current_group) / len(current_group)
        species_list.append(
            Species(
                name=f"{agent.domain.name}-sp{len(species_list)}",
                members=current_group,
                centroid_fitness=centroid,
            )
        )

    return species_list


def apply_elitism(
    agent: SovereignAgent,
    elite_fraction: float = 0.2,
) -> list[SubAgent]:
    """Mark the top `elite_fraction` subagents as protected.

    Protected subagents skip negative mutations for one cycle.
    Returns the list of elite subagents.
    """
    n_elite = max(1, int(len(agent.subagents) * elite_fraction))
    ranked = sorted(agent.subagents, key=lambda s: s.fitness, reverse=True)
    elites = ranked[:n_elite]

    for elite in elites:
        elite.parameters["_elite_shield"] = True

    logger.debug(
        "Elitism: %d/%d subagents shielded in %s (min_elite_fit=%.1f)",
        n_elite,
        len(agent.subagents),
        agent.domain.name,
        elites[-1].fitness if elites else 0,
    )
    return elites
