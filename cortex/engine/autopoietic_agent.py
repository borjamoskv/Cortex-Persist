# [C5-REAL] Exergy-Maximized
"""Autopoietic Agent - Level 7: Self-Modifying Runtime.

The highest level in the agent capability matrix. This agent:
1. REIFIES its own code/strategy as manipulable data (genome)
2. GENERATES variants of itself through mutation operators
3. EVALUATES variants empirically in a fitness arena
4. ADOPTS winning variants and DISCARDS losers
5. MODIFIES its own mutation operators (meta-evolution)
6. SPAWNS entirely new agent types (genesis)
7. EVOLVES its own architecture over time

Reality Level: C5-REAL
"""

from __future__ import annotations

import logging
import random
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

from cortex.engine._autopoietic_helper import (
    adopt,
    apply_meta_mutation,
    checkpoint,
    escalate_mutation_pressure,
    evaluate_genome,
    rollback,
    spawn_from_evolved,
    validate_genome,
)
from cortex.engine._autopoietic_oracle import EvolutionConfig, FitnessOracle
from cortex.engine._autopoietic_state import AutopoieticState
from cortex.engine.genesis import (
    GenesisEngine,
)
from cortex.engine.genome import (
    GenomeMutator,
    StrategyGenome,
)
from cortex.isa.builder import AgentOp

__all__ = [
    "AutopoieticAgent",
    "AutopoieticState",
    "EvolutionConfig",
]

logger = logging.getLogger("cortex.engine.autopoietic_agent")


class AutopoieticAgent:
    """Level 7 Self-Modifying Agent."""

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
        """Run ONE evolution cycle: generate variants → evaluate → select."""
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
            checkpoint(self)

        # ── 2. Evaluate current genome baseline ────────────────
        current_fitness = await evaluate_genome(self, self._genome)
        
        last_fitness_record = self._genome.lineage.fitness_history[-1] if self._genome.lineage.fitness_history else None
        failure_trace = last_fitness_record.metadata.get("failure_trace") if last_fitness_record else None

        # ── 3. Generate variants ───────────────────────────────
        variants = []
        for _ in range(self.config.variants_per_cycle):
            variant = self._mutator.mutate(self._genome, failure_trace=failure_trace)

            # Validate constraints
            if validate_genome(self, variant):
                variants.append((variant, None))
                report["variants_generated"] += 1
                self.state.total_mutations += 1

        # ── 4. Evaluate variants ───────────────────────────────
        variant_scores = []
        for variant, _mt in variants:
            fitness = await evaluate_genome(self, variant)
            variant_scores.append((variant, fitness))
            report["variants_evaluated"] += 1

        # ── 5. Select best variant ─────────────────────────────
        if variant_scores:
            best_variant, best_fitness = max(variant_scores, key=lambda x: x[1])
            improvement = best_fitness - current_fitness

            if improvement > self.config.improvement_threshold:
                # ADOPT: the variant is better
                adopt(self, best_variant)
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
                    escalate_mutation_pressure(self)
                    report["stagnation_escalation"] = True

        # ── 6. Meta-mutation ───────────────────────────────────
        if self.config.enable_meta_mutation and random.random() < 0.15:
            apply_meta_mutation(self)
            report["meta_mutations"] = 1
            self.state.meta_mutations += 1

        # ── 7. Genesis (optional) ──────────────────────────────
        if (
            self.config.enable_genesis
            and self._genesis
            and self.state.current_generation % 10 == 0
            and self._genome.lineage.avg_fitness > 0.7
        ):
            spawn_from_evolved(self)
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
        """Run continuous evolution until convergence or limit."""
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

    def rollback(self, steps: int = 1) -> bool:
        """Rollback to a previous genome checkpoint."""
        return rollback(self, steps)

    # ── Introspection ─────────────────────────────────────────

    def introspect(self) -> dict[str, Any]:
        """Full self-inspection: genome + state + history."""
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
        checkpoint(self)
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
