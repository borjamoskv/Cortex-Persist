# cortex/evolution/agents.py
"""Sovereign Agent & SubAgent definitions for the Continuous Improvement Engine.

10 primary agents, each commanding 10 subagents (100 total).
Each agent has a domain, fitness score, and mutation history.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


class AgentDomain(Enum):
    """The 10 sovereign domains that agents operate in."""

    FABRICATION = auto()  # Code generation / aether
    ORCHESTRATION = auto()  # Pipeline coordination / keter
    SWARM = auto()  # Multi-agent dispatch / legion
    EVOLUTION = auto()  # Self-improvement / ouroboros
    SECURITY = auto()  # Threat detection / boveda
    PERCEPTION = auto()  # Context sensing / neural
    MEMORY = auto()  # Fact storage & recall / cortex core
    EXPERIENCE = auto()  # UI/UX excellence / impactv
    COMMUNICATION = auto()  # Cross-project sync / nexus
    VERIFICATION = auto()  # Quality assurance / mejoralo
    SYNERGY = auto()  # Cross-domain meta-agents / singularity


class MutationType(Enum):
    """Types of improvements a subagent can undergo."""

    PARAMETER_TUNE = auto()
    STRATEGY_SWAP = auto()
    HEURISTIC_INJECT = auto()
    PRUNE_DEAD_PATH = auto()
    BRIDGE_IMPORT = auto()
    ADVERSARIAL_STRESS = auto()
    ENTROPY_REDUCTION = auto()
    CROSSOVER_RECOMBINE = auto()
    STAGNATION_BREAK = auto()
    LATERAL_TRANSFER = auto()  # Plásmidos: Cross-sovereign parameter infection
    EPIGENETIC_SHIFT = auto()  # Transient hormone-driven adaptation


@dataclass
class Mutation:
    """Record of a single improvement applied."""

    mutation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mutation_type: MutationType = MutationType.PARAMETER_TUNE
    description: str = ""
    delta_fitness: float = 0.0
    epigenetic_tags: dict[str, Any] = field(default_factory=dict)  # 350/100: Hormonal context
    timestamp: float = field(default_factory=time.time)


@dataclass
class SubAgent:
    """A specialized worker under a primary agent."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    domain: AgentDomain = AgentDomain.FABRICATION
    fitness: float = 50.0
    parameters: dict[str, Any] = field(default_factory=dict)
    mutations: list[Mutation] = field(default_factory=list)
    epigenetic_state: dict[str, Any] = field(default_factory=dict)  # 350-Sovereign biological state
    generation: int = 0

    @property
    def mutation_count(self) -> int:
        return len(self.mutations)

    def apply_mutation(self, mutation: Mutation) -> None:
        """Apply a mutation and update fitness.

        Note: ceiling enforcement is handled by FitnessLandscape.clamp()
        in the engine — not here.  We only enforce the floor (0.0).
        """
        self.fitness = max(0.0, self.fitness + mutation.delta_fitness)
        self.mutations.append(mutation)
        self.generation += 1
        logger.debug(
            "SubAgent %s mutated: %s (fitness=%.1f, gen=%d)",
            self.id,
            mutation.mutation_type.name,
            self.fitness,
            self.generation,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain.name,
            "fitness": round(self.fitness, 2),
            "generation": self.generation,
            "mutation_count": self.mutation_count,
        }


@dataclass
class SovereignAgent:
    """A primary agent commanding 10 subagents within a domain."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    domain: AgentDomain = AgentDomain.FABRICATION
    fitness: float = 50.0
    subagents: list[SubAgent] = field(default_factory=list)
    mutations: list[Mutation] = field(default_factory=list)
    generation: int = 0
    _cycle_count: int = 0

    def __post_init__(self) -> None:
        """Spawn 10 subagents if none exist."""
        if not self.subagents:
            self.subagents = [
                SubAgent(
                    name=f"{self.domain.name.lower()}-sub-{i}",
                    domain=self.domain,
                )
                for i in range(10)
            ]

    @property
    def avg_subagent_fitness(self) -> float:
        if not self.subagents:
            return 0.0
        return sum(s.fitness for s in self.subagents) / len(self.subagents)

    @property
    def best_subagent(self) -> SubAgent | None:
        if not self.subagents:
            return None
        return max(self.subagents, key=lambda s: s.fitness)

    @property
    def worst_subagent(self) -> SubAgent | None:
        if not self.subagents:
            return None
        return min(self.subagents, key=lambda s: s.fitness)

    def apply_mutation(self, mutation: Mutation) -> None:
        # Ceiling enforcement by FitnessLandscape.clamp() — only floor here.
        self.fitness = max(0.0, self.fitness + mutation.delta_fitness)
        self.mutations.append(mutation)
        self.generation += 1

    def increment_cycle(self) -> None:
        self._cycle_count += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain.name,
            "fitness": round(self.fitness, 2),
            "generation": self.generation,
            "cycles": self._cycle_count,
            "avg_subagent_fitness": round(self.avg_subagent_fitness, 2),
            "subagents": [s.to_dict() for s in self.subagents],
        }


def create_sovereign_swarm() -> list[SovereignAgent]:
    """Instantiate the full 10-agent, 100-subagent swarm."""
    agents = [SovereignAgent(domain=domain) for domain in AgentDomain]
    total_subs = sum(len(a.subagents) for a in agents)
    logger.info(
        "Sovereign swarm spawned: %d agents, %d subagents",
        len(agents),
        total_subs,
    )
    return agents
