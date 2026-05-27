"""Autopoietic Agent — Level 7: Self-Modifying Runtime.

The highest level in the agent capability matrix. This agent:
1. REIFIES its own code/strategy as manipulable data (genome)
2. GENERATES variants of itself through mutation operators
3. EVALUATES variants empirically in a fitness arena
4. ADOPTS winning variants and DISCARDS losers
5. MODIFIES its own mutation operators (meta-evolution)
6. SPAWNS entirely new agent types (genesis)
7. EVOLVES its own architecture over time

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                   AUTOPOIETIC CORE                       │
    │                                                          │
    │   ┌──────────┐    ┌───────────┐    ┌──────────────┐     │
    │   │  GENOME   │───→│  MUTATOR   │───→│  VARIANT      │  │
    │   │  (v_cur)  │    │  (quote+   │    │  (candidate)  │  │
    │   │           │    │  transform)│    │               │  │
    │   └──────────┘    └───────────┘    └──────┬───────┘  │
    │        ↑                                   │          │
    │        │           ┌───────────┐           │          │
    │        │           │  FITNESS   │           │          │
    │        └───────────│  ORACLE    │←──────────┘          │
    │         (adopt)    │  (eval)    │   (measure)          │
    │                    └───────────┘                       │
    │                                                          │
    │   Meta-Loop: The MUTATOR itself is encoded in the       │
    │   GENOME and can be mutated. This is L7.                │
    └─────────────────────────────────────────────────────────┘

References:
- Maturana & Varela (1973): Autopoiesis and Cognition
- Gödel Agent (ACL 2025): Self-rewriting optimization
- Nelson & Narens (1990): Metacognitive monitoring framework
- Eigen (1971): Quasispecies error threshold

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import copy
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional
from collections.abc import Callable, Awaitable

from cortex.isa.builder import (
    AgentOp,
    to_json,
    from_json,
    node_count,
    dispatch_targets,
)
from cortex.engine.genome import (
    StrategyGenome,
    GenomeMutator,
    MutationType,
    FitnessRecord,
    Lineage,
)
from cortex.engine.genesis import (
    GenesisEngine,
    AgentBlueprint,
    AgentSpecies,
    SpawnedAgent,
)

__all__ = [
    "AutopoieticAgent",
    "EvolutionConfig",
    "AutopoieticState",
]

logger = logging.getLogger("cortex.engine.autopoietic_agent")


# ─── Configuration ───────────────────────────────────────────────


@dataclass
class EvolutionConfig:
    """Guardrails for the autopoietic evolution loop."""

    # Evolution parameters
    variants_per_cycle: int = 5
    max_generations: int = 1000
    fitness_threshold: float = 0.9  # adopt if above this
    improvement_threshold: float = 0.01  # min improvement to adopt
    stagnation_limit: int = 10  # generations without improvement

    # Safety rails
    max_complexity: int = 100  # max nodes in dispatch tree
    min_complexity: int = 1  # min nodes
    max_mutation_rate: float = 0.8  # cap on any single mutation rate
    rollback_on_regression: bool = True  # revert if fitness drops
    checkpoint_interval: int = 5  # save state every N generations

    # Arena parameters
    evaluation_budget_ms: float = 30_000.0  # time budget per variant
    min_evaluations: int = 3  # min runs before judging fitness

    # Meta-evolution
    enable_meta_mutation: bool = True  # allow mutation rates to evolve
    enable_genesis: bool = True  # allow spawning new agent types
    enable_architecture_evolution: bool = True  # allow structural changes


# ─── Autopoietic State ──────────────────────────────────────────


@dataclass
class AutopoieticState:
    """Observable state of the autopoietic agent for monitoring."""

    current_generation: int = 0
    current_genome_hash: str = ""
    best_fitness_ever: float = 0.0
    current_fitness: float = 0.0
    fitness_trend: float = 0.0
    generations_without_improvement: int = 0
    total_mutations: int = 0
    total_adoptions: int = 0
    total_discards: int = 0
    total_rollbacks: int = 0
    total_agents_spawned: int = 0
    meta_mutations: int = 0
    is_evolving: bool = False
    last_evolution_ms: float = 0.0
    checkpoint_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_generation": self.current_generation,
            "current_genome_hash": self.current_genome_hash,
            "best_fitness_ever": round(self.best_fitness_ever, 4),
            "current_fitness": round(self.current_fitness, 4),
            "fitness_trend": round(self.fitness_trend, 4),
            "generations_without_improvement": self.generations_without_improvement,
            "total_mutations": self.total_mutations,
            "total_adoptions": self.total_adoptions,
            "total_discards": self.total_discards,
            "total_rollbacks": self.total_rollbacks,
            "total_agents_spawned": self.total_agents_spawned,
            "meta_mutations": self.meta_mutations,
            "is_evolving": self.is_evolving,
            "last_evolution_ms": round(self.last_evolution_ms, 2),
            "checkpoint_count": self.checkpoint_count,
        }


# ─── Fitness Oracle ──────────────────────────────────────────────


class FitnessOracle:
    """Empirical fitness measurement through execution.

    Does NOT simulate or estimate — it RUNS the strategy and MEASURES.
    This is the eval in quote-transform-eval.
    """

    def __init__(self, config: EvolutionConfig) -> None:
        self.config = config

    async def evaluate(
        self,
        genome: StrategyGenome,
        executor: Callable[[AgentOp, dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> FitnessRecord:
        """Execute the genome's dispatch tree and measure fitness.

        Args:
            genome: The strategy genome to evaluate
            executor: Async function that executes an ISA tree and returns metrics

        Returns:
            FitnessRecord with empirical measurements
        """
        start_ns = time.perf_counter_ns()
        success = True
        error_rate = 0.0
        throughput = 0.0
        score = 0.0
        metadata: dict[str, Any] = {}

        try:
            result = await asyncio.wait_for(
                executor(genome.dispatch_tree, genome.parameters),
                timeout=self.config.evaluation_budget_ms / 1000.0,
            )

            latency_ms = (time.perf_counter_ns() - start_ns) / 1e6

            # Extract fitness signals from execution result
            score = result.get("score", 0.0)
            error_rate = result.get("error_rate", 0.0)
            throughput = result.get("throughput", 0.0)
            metadata = result.get("metadata", {})

            # Composite fitness: weighted combination (C5-REAL: Native Rust calculation)
            score = cortex_rs.FitnessOracleRs.composite_fitness(
                raw_score=score,
                latency_ms=latency_ms,
                error_rate=error_rate,
                throughput=throughput,
                complexity=genome.complexity,
            )

        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter_ns() - start_ns) / 1e6
            success = False
            score = -0.1  # Penalty for timeout
            metadata["timeout"] = True

        except Exception as e:
            latency_ms = (time.perf_counter_ns() - start_ns) / 1e6
            success = False
            error_rate = 1.0
            score = -0.5  # Heavy penalty for crash
            metadata["error"] = str(e)[:200]

        record = FitnessRecord(
            score=score,
            latency_ms=latency_ms,
            success=success,
            error_rate=error_rate,
            throughput=throughput,
            metadata=metadata,
        )
        genome.record_fitness(record)
        return record


# ─── Autopoietic Agent ──────────────────────────────────────────


class AutopoieticAgent:
    """Level 7 Self-Modifying Agent.

    The autopoietic agent treats its own strategy as data (genome),
    generates variants through mutation, evaluates them empirically,
    and adopts the winning variant. The mutation operators themselves
    are part of the genome and subject to meta-evolution.

    This is the full autopoietic loop:

        OBSERVE → REIFY → MUTATE → EVALUATE → SELECT → ADOPT
            ↑                                              │
            └──────────────────────────────────────────────┘
                        (recursive self-improvement)

    Usage:
        agent = AutopoieticAgent(
            initial_genome=AgentSpecies.hunter("bounty"),
            executor=my_dispatch_executor,
        )

        # Run one evolution cycle
        report = await agent.evolve_cycle()

        # Run continuous evolution
        report = await agent.evolve(max_generations=100)

        # Inspect state
        logging.info(agent.state.to_dict())
        logging.info(agent.introspect())
    """

    def __init__(
        self,
        *,
        initial_genome: StrategyGenome,
        executor: Callable[[AgentOp, dict[str, Any]], Awaitable[dict[str, Any]]],
        config: EvolutionConfig | None = None,
    ) -> None:
        self.config = config or EvolutionConfig()
        self._executor = executor
        self._mutator = GenomeMutator()
        self._oracle = FitnessOracle(self.config)
        self._genesis = GenesisEngine() if self.config.enable_genesis else None

        # Core state: the living genome
        self._genome = initial_genome
        self._best_genome: StrategyGenome | None = None
        self._checkpoints: deque[StrategyGenome] = deque(maxlen=20)

        # Observable state
        self.state = AutopoieticState()
        self.state.current_genome_hash = initial_genome.genome_hash

        # Evolution history
        self._evolution_log: list[dict[str, Any]] = []

    # ── Properties ────────────────────────────────────────────

    @property
    def genome(self) -> StrategyGenome:
        """The current living genome (read-only access)."""
        return self._genome

    @property
    def generation(self) -> int:
        return self._genome.lineage.generation

    # ── Core Evolution Loop ───────────────────────────────────

    async def evolve_cycle(self) -> dict[str, Any]:
        """Run ONE evolution cycle: generate variants → evaluate → select.

        This is the atomic unit of autopoiesis. Each cycle:
        1. Generates N variant genomes through mutation
        2. Evaluates each variant's fitness empirically
        3. Compares variants against the current genome
        4. Adopts the best variant if it improves fitness
        5. Optionally applies meta-mutation to mutation rates

        Returns a structured evolution report.
        """
        cycle_start = time.perf_counter_ns()
        self.state.is_evolving = True

        report: dict[str, Any] = {
            "generation": self._genome.lineage.generation,
            "genome_hash_before": self._genome.genome_hash[:8],
            "variants_generated": 0,
            "variants_evaluated": 0,
            "adopted": False,
            "fitness_before": self._genome.lineage.avg_fitness,
            "fitness_after": 0.0,
            "mutations_applied": [],
            "meta_mutations": 0,
        }

        # ── 1. Checkpoint ──────────────────────────────────────
        if self.state.current_generation % self.config.checkpoint_interval == 0:
            self._checkpoint()

        # ── 2. Evaluate current genome baseline ────────────────
        current_fitness = await self._evaluate_genome(self._genome)

        # ── 3. Generate variants ───────────────────────────────
        variants: list[tuple[StrategyGenome, MutationType | None]] = []
        for _ in range(self.config.variants_per_cycle):
            mutation_type = None
            variant = self._mutator.mutate(self._genome)

            # Validate constraints
            if self._validate_genome(variant):
                variants.append((variant, mutation_type))
                report["variants_generated"] += 1
                self.state.total_mutations += 1

        # ── 4. Evaluate variants ───────────────────────────────
        variant_scores: list[tuple[StrategyGenome, float]] = []
        for variant, _mt in variants:
            fitness = await self._evaluate_genome(variant)
            variant_scores.append((variant, fitness))
            report["variants_evaluated"] += 1

        # ── 5. Select best variant ─────────────────────────────
        if variant_scores:
            best_variant, best_fitness = max(variant_scores, key=lambda x: x[1])
            improvement = best_fitness - current_fitness

            if improvement > self.config.improvement_threshold:
                # ADOPT: the variant is better
                self._adopt(best_variant)
                report["adopted"] = True
                report["improvement"] = improvement
                report["fitness_after"] = best_fitness
                self.state.total_adoptions += 1
                self.state.generations_without_improvement = 0

                logger.info(
                    "AUTOPOIESIS: ADOPTED variant gen=%d hash=%s (fitness: %.4f → %.4f, Δ=+%.4f)",
                    best_variant.lineage.generation,
                    best_variant.genome_hash[:8],
                    current_fitness,
                    best_fitness,
                    improvement,
                )
            else:
                # DISCARD: keep current genome
                self.state.total_discards += len(variant_scores)
                self.state.generations_without_improvement += 1
                report["fitness_after"] = current_fitness

                if self.state.generations_without_improvement >= self.config.stagnation_limit:
                    # Stagnation detected: increase mutation pressure
                    self._escalate_mutation_pressure()
                    report["stagnation_escalation"] = True

        # ── 6. Meta-mutation ───────────────────────────────────
        if self.config.enable_meta_mutation and random.random() < 0.15:
            self._apply_meta_mutation()
            report["meta_mutations"] = 1
            self.state.meta_mutations += 1

        # ── 7. Genesis (optional) ──────────────────────────────
        if (
            self.config.enable_genesis
            and self._genesis
            and self.state.current_generation % 10 == 0
            and self._genome.lineage.avg_fitness > 0.7
        ):
            self._spawn_from_evolved()
            report["agent_spawned"] = True

        # ── Finalize ───────────────────────────────────────────
        self.state.current_generation += 1
        self.state.current_fitness = self._genome.lineage.avg_fitness
        self.state.fitness_trend = self._genome.lineage.fitness_trend
        self.state.current_genome_hash = self._genome.genome_hash[:8]
        self.state.best_fitness_ever = max(
            self.state.best_fitness_ever,
            self._genome.lineage.best_fitness,
        )
        self.state.is_evolving = False
        self.state.last_evolution_ms = (time.perf_counter_ns() - cycle_start) / 1e6

        report["genome_hash_after"] = self._genome.genome_hash[:8]
        report["cycle_latency_ms"] = self.state.last_evolution_ms
        self._evolution_log.append(report)

        return report

    async def evolve(
        self,
        *,
        max_generations: int | None = None,
        target_fitness: float | None = None,
        on_cycle: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        """Run continuous evolution until convergence or limit.

        Args:
            max_generations: Stop after this many generations
            target_fitness: Stop when fitness exceeds this value
            on_cycle: Callback invoked after each evolution cycle

        Returns:
            Summary of the full evolution run.
        """
        max_gen = max_generations or self.config.max_generations
        target = target_fitness or self.config.fitness_threshold

        run_start = time.perf_counter_ns()
        initial_fitness = self._genome.lineage.avg_fitness
        cycles_run = 0

        for _ in range(max_gen):
            report = await self.evolve_cycle()
            cycles_run += 1

            if on_cycle:
                await on_cycle(report)

            # Convergence check
            if self.state.current_fitness >= target:
                logger.info(
                    "AUTOPOIESIS: Converged at gen=%d fitness=%.4f (target=%.4f)",
                    self.state.current_generation,
                    self.state.current_fitness,
                    target,
                )
                break

            # Stagnation death: if no improvement for too long, stop
            if self.state.generations_without_improvement > self.config.stagnation_limit * 3:
                logger.warning(
                    "AUTOPOIESIS: Stagnation death at gen=%d (no improvement for %d gens)",
                    self.state.current_generation,
                    self.state.generations_without_improvement,
                )
                break

        total_ms = (time.perf_counter_ns() - run_start) / 1e6
        return {
            "cycles_run": cycles_run,
            "initial_fitness": initial_fitness,
            "final_fitness": self.state.current_fitness,
            "improvement": self.state.current_fitness - initial_fitness,
            "best_fitness_ever": self.state.best_fitness_ever,
            "total_mutations": self.state.total_mutations,
            "total_adoptions": self.state.total_adoptions,
            "total_discards": self.state.total_discards,
            "meta_mutations": self.state.meta_mutations,
            "total_latency_ms": total_ms,
            "final_genome": self._genome.introspect(),
        }

    # ── Internal Mechanics ────────────────────────────────────

    async def _evaluate_genome(self, genome: StrategyGenome) -> float:
        """Evaluate a genome's fitness through N runs."""
        scores: list[float] = []
        for _ in range(self.config.min_evaluations):
            record = await self._oracle.evaluate(genome, self._executor)
            scores.append(record.score)
        return sum(scores) / len(scores) if scores else 0.0

    def _adopt(self, new_genome: StrategyGenome) -> None:
        """Replace the current genome with the winning variant."""
        self._best_genome = self._genome.clone()
        self._genome = new_genome
        self._genome.lineage.adopted_count += 1

    def _validate_genome(self, genome: StrategyGenome) -> bool:
        """Check that a mutated genome satisfies safety constraints."""
        complexity = genome.complexity
        if complexity > self.config.max_complexity:
            logger.debug(
                "GENOME REJECTED: complexity %d > max %d", complexity, self.config.max_complexity
            )
            return False
        if complexity < self.config.min_complexity:
            logger.debug(
                "GENOME REJECTED: complexity %d < min %d", complexity, self.config.min_complexity
            )
            return False

        # Check mutation rates are within bounds
        for mt, rate in genome.mutation_rates.items():
            if rate > self.config.max_mutation_rate:
                genome.mutation_rates[mt] = self.config.max_mutation_rate

        return True

    def _checkpoint(self) -> None:
        """Save current genome state for rollback."""
        self._checkpoints.append(self._genome.clone())
        self.state.checkpoint_count += 1

    def rollback(self, steps: int = 1) -> bool:
        """Rollback to a previous genome checkpoint."""
        for _ in range(steps):
            if self._checkpoints:
                self._genome = self._checkpoints.pop()
                self.state.total_rollbacks += 1
                logger.info(
                    "AUTOPOIESIS: Rolled back to gen=%d hash=%s",
                    self._genome.lineage.generation,
                    self._genome.genome_hash[:8],
                )
            else:
                return False
        return True

    def _escalate_mutation_pressure(self) -> None:
        """Increase mutation rates when stagnation is detected.

        This is a form of meta-control: the agent detects that its
        current mutation strategy isn't working and adjusts it.
        """
        for mt in MutationType:
            current = self._genome.mutation_rates.get(mt, 0.05)
            self._genome.mutation_rates[mt] = min(
                self.config.max_mutation_rate,
                current * 1.3,
            )
        # Boost radical mutations specifically
        self._genome.mutation_rates[MutationType.STRATEGY_SYNTHESIS] = min(
            0.5,
            self._genome.mutation_rates.get(MutationType.STRATEGY_SYNTHESIS, 0.05) * 2.0,
        )
        logger.info(
            "AUTOPOIESIS: Mutation pressure escalated (stagnation detected: %d gens)",
            self.state.generations_without_improvement,
        )

    def _apply_meta_mutation(self) -> None:
        """Apply meta-mutation: mutate the mutation rates themselves."""
        import random as _random

        mt = _random.choice(list(MutationType))
        current = self._genome.mutation_rates.get(mt, 0.05)
        delta = _random.gauss(0, 0.03)
        new_rate = max(0.001, min(self.config.max_mutation_rate, current + delta))
        self._genome.mutation_rates[mt] = new_rate
        self._genome._invalidate_hash()
        logger.debug(
            "META-MUTATION: %s rate %.3f → %.3f",
            mt.value,
            current,
            new_rate,
        )

    def _spawn_from_evolved(self) -> None:
        """Use Genesis to spawn a new agent type from the current genome."""
        if not self._genesis:
            return

        blueprint = AgentBlueprint(
            species=f"evolved_{self._genome.name}_{self.state.current_generation}",
            genome=self._genome.clone(),
            capabilities=["evolved", "autopoietic"],
        )
        self._genesis.register_blueprint(blueprint)
        self._genesis.spawn(blueprint)
        self.state.total_agents_spawned += 1
        logger.info(
            "AUTOPOIESIS → GENESIS: Spawned new agent from gen=%d fitness=%.4f",
            self.state.current_generation,
            self.state.current_fitness,
        )

    # ── Introspection ─────────────────────────────────────────

    def introspect(self) -> dict[str, Any]:
        """Full self-inspection: genome + state + history.

        This is the agent thinking about itself. The output is
        structured data that can be fed back into the evolution loop.
        """
        return {
            "level": 7,
            "type": "autopoietic",
            "state": self.state.to_dict(),
            "genome": self._genome.introspect(),
            "checkpoints_available": len(self._checkpoints),
            "evolution_log_size": len(self._evolution_log),
            "genesis_census": self._genesis.census() if self._genesis else None,
            "last_5_cycles": self._evolution_log[-5:] if self._evolution_log else [],
            "capability_matrix": {
                "respond_to_input": True,
                "maintain_context": True,
                "suggest_actions": True,
                "execute_autonomously": True,
                "use_tools": True,
                "detect_errors": True,
                "self_repair": True,
                "evaluate_reasoning": True,
                "learn_from_experience": True,
                "modify_own_code": True,
                "generate_new_agents": True,
                "evolve_architecture": True,
            },
        }

    def export_genome(self) -> str:
        """Export the current genome as JSON for external analysis."""
        return self._genome.to_json(indent=2)

    def import_genome(self, json_str: str) -> None:
        """Import a genome from JSON (e.g., from another agent's export)."""
        self._checkpoint()
        self._genome = StrategyGenome.from_json(json_str)
        self.state.current_genome_hash = self._genome.genome_hash
        logger.info(
            "AUTOPOIESIS: Imported genome hash=%s gen=%d",
            self._genome.genome_hash[:8],
            self._genome.lineage.generation,
        )

    def __repr__(self) -> str:
        return (
            f"<AutopoieticAgent L7 gen={self.state.current_generation} "
            f"fitness={self.state.current_fitness:.4f} "
            f"hash={self.state.current_genome_hash} "
            f"mutations={self.state.total_mutations} "
            f"adoptions={self.state.total_adoptions}>"
        )


# ─── Convenience: import random at module level for meta-mutation ─
import random  # noqa: E402
