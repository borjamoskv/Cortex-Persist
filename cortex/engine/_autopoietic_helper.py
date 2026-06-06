# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from cortex.engine.genesis import AgentBlueprint
from cortex.engine.genome import MutationType, StrategyGenome

if TYPE_CHECKING:
    from cortex.engine.autopoietic_agent import AutopoieticAgent

logger = logging.getLogger("cortex.engine.autopoietic_agent")


async def evaluate_genome(agent: AutopoieticAgent, genome: StrategyGenome) -> float:
    """Evaluate a genome's fitness through N runs."""
    scores: list[float] = []
    for _ in range(agent.config.min_evaluations):
        record = await agent._oracle.evaluate(genome, agent._executor)
        scores.append(record.score)
    return sum(scores) / len(scores) if scores else 0.0


def adopt(agent: AutopoieticAgent, new_genome: StrategyGenome) -> None:
    """Replace the current genome with the winning variant."""
    agent._best_genome = agent._genome.clone()
    agent._genome = new_genome
    agent._genome.lineage.adopted_count += 1


def validate_genome(agent: AutopoieticAgent, genome: StrategyGenome) -> bool:
    """Check that a mutated genome satisfies safety constraints."""
    complexity = genome.complexity
    if complexity > agent.config.max_complexity:
        logger.debug(
            "GENOME REJECTED: complexity %d > max %d", complexity, agent.config.max_complexity
        )
        return False
    if complexity < agent.config.min_complexity:
        logger.debug(
            "GENOME REJECTED: complexity %d < min %d", complexity, agent.config.min_complexity
        )
        return False

    # Check mutation rates are within bounds
    for mt, rate in genome.mutation_rates.items():
        if rate > agent.config.max_mutation_rate:
            genome.mutation_rates[mt] = agent.config.max_mutation_rate

    return True


def checkpoint(agent: AutopoieticAgent) -> None:
    """Save current genome state for rollback."""
    agent._checkpoints.append(agent._genome.clone())
    agent.state.checkpoint_count += 1


def rollback(agent: AutopoieticAgent, steps: int = 1) -> bool:
    """Rollback to a previous genome checkpoint."""
    for _ in range(steps):
        if agent._checkpoints:
            agent._genome = agent._checkpoints.pop()
            agent.state.total_rollbacks += 1
            logger.info(
                "AUTOPOIESIS: Rolled back to gen=%d hash=%s",
                agent._genome.lineage.generation,
                agent._genome.genome_hash[:8],
            )
        else:
            return False
    return True


def escalate_mutation_pressure(agent: AutopoieticAgent) -> None:
    """Increase mutation rates when stagnation is detected."""
    for mt in MutationType:
        current = agent._genome.mutation_rates.get(mt, 0.05)
        agent._genome.mutation_rates[mt] = min(
            agent.config.max_mutation_rate,
            current * 1.3,
        )
    # Boost radical mutations specifically
    agent._genome.mutation_rates[MutationType.STRATEGY_SYNTHESIS] = min(
        0.5,
        agent._genome.mutation_rates.get(MutationType.STRATEGY_SYNTHESIS, 0.05) * 2.0,
    )
    logger.info(
        "AUTOPOIESIS: Mutation pressure escalated (stagnation detected: %d gens)",
        agent.state.generations_without_improvement,
    )


def apply_meta_mutation(agent: AutopoieticAgent) -> None:
    """Apply meta-mutation: mutate the mutation rates themselves."""
    mt = random.choice(list(MutationType))
    current = agent._genome.mutation_rates.get(mt, 0.05)
    delta = random.gauss(0, 0.03)
    new_rate = max(0.001, min(agent.config.max_mutation_rate, current + delta))
    agent._genome.mutation_rates[mt] = new_rate
    agent._genome._invalidate_hash()
    logger.debug(
        "META-MUTATION: %s rate %.3f → %.3f",
        mt.value,
        current,
        new_rate,
    )


def spawn_from_evolved(agent: AutopoieticAgent) -> None:
    """Use Genesis to spawn a new agent type from the current genome."""
    if not agent._genesis:
        return

    blueprint = AgentBlueprint(
        species=f"evolved_{agent._genome.name}_{agent.state.current_generation}",
        genome=agent._genome.clone(),
        capabilities=["evolved", "autopoietic"],
    )
    agent._genesis.register_blueprint(blueprint)
    agent._genesis.spawn(blueprint)
    agent.state.total_agents_spawned += 1
    logger.info(
        "AUTOPOIESIS → GENESIS: Spawned new agent from gen=%d fitness=%.4f",
        agent.state.current_generation,
        agent.state.current_fitness,
    )
