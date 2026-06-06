# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import cortex_rs
from cortex.engine.genome import FitnessRecord, StrategyGenome
from cortex.isa.builder import AgentOp


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


class FitnessOracle:
    """Empirical fitness measurement through execution.

    Does NOT simulate or estimate - it RUNS the strategy and MEASURES.
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
            score = cortex_rs.FitnessOracleRs.composite_fitness(  # pyright: ignore[reportAttributeAccessIssue]
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
