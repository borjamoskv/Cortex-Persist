# [C5-REAL] Exergy-Maximized
"""Agent Genesis - L7 Factory for Spawning New Agent Types.

The Genesis engine creates entirely new agent types from evolved genomes.
This is the "generate new agents" capability of L7:

1. COMPOSE - Combine winning genome fragments into new architectures
2. SPECIALIZE - Create domain-specific agents from general templates
3. SPAWN - Instantiate agents with evolved dispatch trees
4. REGISTER - Add new agent types to the runtime registry

The Genesis engine does NOT use exec() or eval() on raw strings.
All agent creation flows through the ISA builder's type-safe DSL,
ensuring structural validity at construction time.

Reality Level: C5-REAL
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from babylon60.engine.genome import FitnessRecord, GenomeMutator, StrategyGenome
from babylon60.isa.builder import (
    Predicate,
    bind,
    cond,
    dispatch,
    halt,
    par,
    seq,
)

__all__ = [
    "AgentBlueprint",
    "AgentSpecies",
    "GenesisEngine",
    "SpawnedAgent",
]

logger = logging.getLogger("babylon60.engine.genesis")


# ─── Agent Blueprint ─────────────────────────────────────────────


@dataclass
class AgentBlueprint:
    """Template for a new agent type.

    Combines a genome with execution metadata to create
    a fully instantiable agent definition.
    """

    species: str
    genome: StrategyGenome
    capabilities: list[str] = field(default_factory=list)
    resource_budget: dict[str, float] = field(default_factory=dict)
    max_concurrent: int = 1
    ttl_seconds: float = 300.0
    created_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "species": self.species,
            "genome": self.genome.to_dict(),
            "capabilities": self.capabilities,
            "resource_budget": self.resource_budget,
            "max_concurrent": self.max_concurrent,
            "ttl_seconds": self.ttl_seconds,
            "created_at": self.created_at,
        }


@dataclass
class SpawnedAgent:
    """A live agent instance created by Genesis."""

    agent_id: str
    blueprint: AgentBlueprint
    state: str = "idle"  # idle, running, completed, failed, terminated
    spawn_time: float = field(default_factory=time.monotonic)
    fitness_records: list[FitnessRecord] = field(default_factory=list)
    execution_count: int = 0
    error_count: int = 0

    @property
    def is_alive(self) -> bool:
        elapsed = time.monotonic() - self.spawn_time
        return (
            self.state not in ("completed", "failed", "terminated")
            and elapsed < self.blueprint.ttl_seconds
        )

    @property
    def health_score(self) -> float:
        if self.execution_count == 0:
            return 1.0
        return max(0.0, 1.0 - (self.error_count / self.execution_count))

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "species": self.blueprint.species,
            "state": self.state,
            "is_alive": self.is_alive,
            "health_score": self.health_score,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "genome_hash": self.blueprint.genome.genome_hash,
        }


# ─── Agent Species Templates ────────────────────────────────────


class AgentSpecies:
    """Predefined species templates for agent generation.

    Each species defines a structural archetype that Genesis can
    instantiate, parameterize, and evolve. These are the "seed"
    genomes that evolution operates on.
    """

    @staticmethod
    def hunter(domain: str = "general", targets: int = 3) -> StrategyGenome:
        """Fan-out hunter: parallel scan → aggregate → report."""
        hunters = [
            dispatch(
                f"hunter_{domain}_{i}",
                {"mode": "scan", "domain": domain},
                id=100 + i,
            )
            for i in range(targets)
        ]
        tree = seq(
            bind("domain", domain),
            par(*hunters),
            dispatch("aggregator", {"collect": True, "domain": domain}, id=200),
            dispatch("reporter", {"emit": True}, id=300),
        )
        return StrategyGenome(
            name=f"hunter_{domain}",
            dispatch_tree=tree,
            parameters={
                "scan_depth": 3,
                "timeout_ms": 5000,
                "min_confidence": 0.7,
            },
            constraints=["must_have_aggregator", "min_hunters_2"],
        )

    @staticmethod
    def pipeline(stages: list[str] | None = None) -> StrategyGenome:
        """Sequential pipeline: ingest → process → validate → emit."""
        stages = stages or ["ingest", "process", "validate", "emit"]
        tree = seq(
            *[
                dispatch(
                    f"pipeline_{stage}",
                    {"phase": i + 1, "stage": stage},
                    id=100 + i,
                )
                for i, stage in enumerate(stages)
            ]
        )
        return StrategyGenome(
            name="pipeline",
            dispatch_tree=tree,
            parameters={
                "batch_size": 100,
                "retry_count": 2,
                "checkpoint_interval": 50,
            },
            constraints=["sequential_order_preserved"],
        )

    @staticmethod
    def guardian(domain: str = "security") -> StrategyGenome:
        """Conditional guardian: scan → decide → act or alert."""
        tree = seq(
            dispatch("guardian_scan", {"domain": domain}, id=100),
            cond(
                Predicate.always(),
                then_branch=seq(
                    dispatch("guardian_act", {"mode": "enforce"}, id=201),
                    dispatch("guardian_log", {"mode": "audit"}, id=202),
                ),
                else_branch=dispatch("guardian_alert", {"severity": "high"}, id=300),
            ),
        )
        return StrategyGenome(
            name=f"guardian_{domain}",
            dispatch_tree=tree,
            parameters={
                "threat_threshold": 0.8,
                "alert_cooldown_ms": 10000,
                "max_enforcement_level": 3,
            },
            constraints=["must_log_actions", "alert_on_failure"],
        )

    @staticmethod
    def explorer(depth: int = 3) -> StrategyGenome:
        """Recursive explorer: scout → evaluate → branch → recurse."""
        inner = dispatch("explorer_evaluate", {"depth": depth}, id=100)
        for d in range(depth):
            inner = seq(
                dispatch(f"explorer_scout_{d}", {"level": d}, id=200 + d),
                cond(
                    Predicate.always(),
                    then_branch=inner,
                    else_branch=halt(error=f"dead_end_depth_{d}"),
                ),
            )
        return StrategyGenome(
            name="explorer",
            dispatch_tree=inner,
            parameters={
                "max_depth": depth,
                "branch_factor": 2,
                "curiosity_weight": 0.6,
            },
        )

    @staticmethod
    def swarm_coordinator(swarm_size: int = 5) -> StrategyGenome:
        """Swarm coordinator: init → fan-out workers → collect → synthesize."""
        workers = [
            dispatch(
                f"swarm_worker_{i}",
                {"worker_id": i},
                id=100 + i,
            )
            for i in range(swarm_size)
        ]
        tree = seq(
            dispatch("swarm_init", {"size": swarm_size}, id=50),
            par(*workers),
            dispatch("swarm_collect", {"expected": swarm_size}, id=200),
            dispatch("swarm_synthesize", {}, id=300),
        )
        return StrategyGenome(
            name="swarm_coordinator",
            dispatch_tree=tree,
            parameters={
                "swarm_size": swarm_size,
                "consensus_threshold": 0.67,
                "timeout_per_worker_ms": 3000,
            },
            constraints=["quorum_required"],
        )


# ─── Genesis Engine ──────────────────────────────────────────────


class GenesisEngine:
    """Factory for spawning, evolving, and managing agent populations.

    Capabilities:
    1. Create agents from species templates
    2. Evolve agents through mutation and crossover
    3. Run fitness tournaments to select winners
    4. Spawn new agent types from winning genomes
    5. Maintain a species registry for runtime discovery

    This is the "generate new agents" and "evolve architecture"
    capabilities from the L7 matrix.
    """

    def __init__(self, *, population_cap: int = 50) -> None:
        self.population_cap = population_cap
        self.mutator = GenomeMutator()
        self._registry: dict[str, AgentBlueprint] = {}
        self._population: dict[str, SpawnedAgent] = {}
        self._graveyard: list[dict[str, Any]] = []
        self._generation_counter = 0

    # ── Registry ──────────────────────────────────────────────

    def register_blueprint(self, blueprint: AgentBlueprint) -> str:
        """Register a new agent blueprint in the species registry."""
        key = f"{blueprint.species}_{blueprint.genome.genome_hash[:8]}"
        self._registry[key] = blueprint
        logger.info(
            "GENESIS: Registered blueprint '%s' (genome: %s, complexity: %d)",
            key,
            blueprint.genome.genome_hash[:8],
            blueprint.genome.complexity,
        )
        return key

    def get_blueprint(self, key: str) -> AgentBlueprint | None:
        return self._registry.get(key)

    @property
    def registry_keys(self) -> list[str]:
        return list(self._registry.keys())

    # ── Spawning ──────────────────────────────────────────────

    def spawn(
        self,
        blueprint: AgentBlueprint,
        *,
        agent_id: str | None = None,
    ) -> SpawnedAgent:
        """Spawn a live agent from a blueprint."""
        if len(self._population) >= self.population_cap:
            self._cull_weakest()

        aid = agent_id or f"{blueprint.species}_{int(time.monotonic() * 1000) % 1_000_000}"
        agent = SpawnedAgent(agent_id=aid, blueprint=blueprint)
        self._population[aid] = agent
        blueprint.genome.lineage.children_spawned += 1

        logger.info(
            "GENESIS: Spawned agent '%s' (species: %s, genome: %s)",
            aid,
            blueprint.species,
            blueprint.genome.genome_hash[:8],
        )
        return agent

    def spawn_from_species(
        self,
        species_factory: Callable[..., StrategyGenome],
        *,
        species_name: str = "auto",
        **kwargs: Any,
    ) -> SpawnedAgent:
        """Spawn an agent directly from a species template."""
        genome = species_factory(**kwargs)
        blueprint = AgentBlueprint(
            species=species_name if species_name != "auto" else genome.name,
            genome=genome,
        )
        self.register_blueprint(blueprint)
        return self.spawn(blueprint)

    # ── Evolution ─────────────────────────────────────────────

    def evolve_population(
        self,
        *,
        mutations_per_cycle: int = 3,
        crossover_probability: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Run one evolution cycle across the population.

        1. Select parents (fitness-proportionate)
        2. Apply mutations
        3. Optional crossover
        4. Register new blueprints
        5. Cull the weakest

        Returns a log of evolution events.
        """
        self._generation_counter += 1
        events: list[dict[str, Any]] = []
        live_agents = [a for a in self._population.values() if a.is_alive]

        if len(live_agents) < 2:
            logger.info("GENESIS: Population too small for evolution (%d agents)", len(live_agents))
            return events

        # Sort by fitness
        ranked = sorted(
            live_agents, key=lambda a: a.blueprint.genome.lineage.avg_fitness, reverse=True
        )

        # Mutations on top performers
        for agent in ranked[:mutations_per_cycle]:
            child_genome = self.mutator.mutate(agent.blueprint.genome)
            child_blueprint = AgentBlueprint(
                species=f"{agent.blueprint.species}_evolved",
                genome=child_genome,
                capabilities=list(agent.blueprint.capabilities),
                resource_budget=dict(agent.blueprint.resource_budget),
            )
            self.register_blueprint(child_blueprint)
            child_agent = self.spawn(child_blueprint)
            events.append(
                {
                    "type": "mutation",
                    "parent": agent.agent_id,
                    "child": child_agent.agent_id,
                    "generation": self._generation_counter,
                    "genome_hash": child_genome.genome_hash[:8],
                }
            )

        # Crossover between top pairs
        if random.random() < crossover_probability and len(ranked) >= 2:
            parent_a = ranked[0]
            parent_b = ranked[1]
            child_genome = self.mutator.crossover(
                parent_a.blueprint.genome,
                parent_b.blueprint.genome,
            )
            child_blueprint = AgentBlueprint(
                species=f"crossover_{parent_a.blueprint.species}",
                genome=child_genome,
            )
            self.register_blueprint(child_blueprint)
            child_agent = self.spawn(child_blueprint)
            events.append(
                {
                    "type": "crossover",
                    "parent_a": parent_a.agent_id,
                    "parent_b": parent_b.agent_id,
                    "child": child_agent.agent_id,
                    "generation": self._generation_counter,
                }
            )

        # Cull if over capacity
        while len(self._population) > self.population_cap:
            self._cull_weakest()
            events.append({"type": "cull", "generation": self._generation_counter})

        return events

    def compose_hybrid(
        self,
        genomes: list[StrategyGenome],
        *,
        name: str = "hybrid",
        composition: str = "parallel",
    ) -> StrategyGenome:
        """Compose multiple genomes into a single hybrid agent.

        Args:
            genomes: Source genomes to compose
            composition: "parallel" (fan-out) or "sequential" (pipeline)
        """
        trees = [g.dispatch_tree for g in genomes]
        if composition == "parallel":
            combined_tree = par(*trees)
        else:
            combined_tree = seq(*trees)

        # Merge parameters (last writer wins for conflicts)
        merged_params: dict[str, Any] = {}
        for g in genomes:
            merged_params.update(g.parameters)

        # Average mutation rates
        merged_rates: dict[str, float] = {}
        for mt_key in genomes[0].mutation_rates:
            rates = [g.mutation_rates.get(mt_key, 0.05) for g in genomes]
            merged_rates[mt_key] = sum(rates) / len(rates)

        hybrid = StrategyGenome(
            name=name,
            dispatch_tree=combined_tree,
            parameters=merged_params,
            mutation_rates=merged_rates,
            constraints=[f"composed_from_{len(genomes)}_genomes"],
        )
        hybrid.lineage.generation = max(g.lineage.generation for g in genomes) + 1
        hybrid.lineage.parent_hash = "+".join(g.genome_hash[:8] for g in genomes)
        hybrid.lineage.mutation_log.append(f"composed_{composition}_{len(genomes)}_sources")

        return hybrid

    # ── Population Management ─────────────────────────────────

    def _cull_weakest(self) -> None:
        """Remove the weakest agent from the population."""
        if not self._population:
            return

        weakest_id = min(
            self._population,
            key=lambda aid: self._population[aid].blueprint.genome.lineage.avg_fitness,
        )
        agent = self._population.pop(weakest_id)
        agent.state = "terminated"
        agent.blueprint.genome.lineage.discarded_count += 1
        self._graveyard.append(
            {
                "agent_id": weakest_id,
                "species": agent.blueprint.species,
                "fitness": agent.blueprint.genome.lineage.avg_fitness,
                "generation": agent.blueprint.genome.lineage.generation,
                "terminated_at": time.monotonic(),
            }
        )
        logger.info(
            "GENESIS: Culled agent '%s' (fitness: %.2f, gen: %d)",
            weakest_id,
            agent.blueprint.genome.lineage.avg_fitness,
            agent.blueprint.genome.lineage.generation,
        )

    def terminate(self, agent_id: str) -> bool:
        """Terminate a specific agent."""
        agent = self._population.pop(agent_id, None)
        if agent:
            agent.state = "terminated"
            self._graveyard.append(agent.to_dict())
            return True
        return False

    # ── Reporting ─────────────────────────────────────────────

    def census(self) -> dict[str, Any]:
        """Full population census."""
        live = [a for a in self._population.values() if a.is_alive]
        dead = [a for a in self._population.values() if not a.is_alive]
        return {
            "generation": self._generation_counter,
            "population_size": len(self._population),
            "live_agents": len(live),
            "dead_agents": len(dead),
            "graveyard_size": len(self._graveyard),
            "registry_size": len(self._registry),
            "species_distribution": self._species_distribution(),
            "top_agents": [
                {
                    "agent_id": a.agent_id,
                    "species": a.blueprint.species,
                    "fitness": a.blueprint.genome.lineage.avg_fitness,
                    "generation": a.blueprint.genome.lineage.generation,
                    "genome_hash": a.blueprint.genome.genome_hash[:8],
                }
                for a in sorted(
                    live,
                    key=lambda a: a.blueprint.genome.lineage.avg_fitness,
                    reverse=True,
                )[:5]
            ],
        }

    def _species_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for agent in self._population.values():
            species = agent.blueprint.species
            dist[species] = dist.get(species, 0) + 1
        return dist
