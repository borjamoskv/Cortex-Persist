# [C5-REAL] Exergy-Maximized

import asyncio
import logging
import random
import secrets
import sqlite3
from typing import TYPE_CHECKING

from cortex.extensions.evolution.agents import Mutation, SovereignAgent, SubAgent

if TYPE_CHECKING:
    from cortex.extensions.evolution.action import SymbolicActionEngine
    from cortex.extensions.evolution.ledger_db import EvolutionLedgerDB
    from cortex.extensions.evolution.models import EngineParameters
    from cortex.extensions.gate.ouroboros import OuroborosGate
    from cortex.extensions.sovereign.endocrine import DigitalEndocrine
    from cortex.ledger import SovereignLedger
logger = logging.getLogger("cortex.extensions.evolution.engine.ops")


class EvolutionOpsMixin:
    """Mixin for genetic operations, extinctions, and adversarial grounding."""

    if TYPE_CHECKING:
        params: EngineParameters
        sovereigns: list[SovereignAgent]
        cycle_count: int
        _endocrine: DigitalEndocrine
        _ledger: SovereignLedger
        _evolution_ledger: EvolutionLedgerDB
        _ouroboros: OuroborosGate | None
        _action_engine: SymbolicActionEngine
        _broadcast_task: asyncio.Task | None

    def _record_merkle_checkpoint(
        self, agent: SovereignAgent | SubAgent, mutation: Mutation
    ) -> None:
        """Record an immutable checkpoint of the agent state (Phase 2 v3)."""
        logger.info("Axiom 12: Triggering Merkle Checkpoint for %s", agent.id)
        try:
            self._ledger.record_transaction(
                project="cortex-evolution",
                action="evolution_checkpoint",
                detail={
                    "agent_id": agent.id,
                    "mutation_id": mutation.mutation_id,
                    "state_hash": agent.state_hash,
                    "description": mutation.description,
                    "generation": agent.generation,
                },
            )
        except (sqlite3.Error, OSError, RuntimeError) as exc:
            logger.warning("Ledger write failed for agent %s: %s", agent.id, exc)
        agent.mutations.clear()

    def _crossover(self, parent_a: SubAgent, parent_b: SubAgent) -> SubAgent:
        """Perform genetic crossover combining two parent SubAgents into a new offspring."""
        cycle = getattr(self, "cycle_count", 0)
        child = SubAgent(
            id=f"sub_{parent_a.domain.name.lower()}_gen{cycle}_{random.randint(1000, 9999)}",
            domain=parent_a.domain,
            name=f"Offspring-{parent_a.id}x{parent_b.id}",
            generation=max(parent_a.generation, parent_b.generation) + 1,
        )
        child.epigenetic_state = {
            "dopamine_bias": self._endocrine.dopamine,
            "cortisol_bias": self._endocrine.cortisol,
        }
        t_a = parent_a.parameters.get("temperature", 0.5)
        t_b = parent_b.parameters.get("temperature", 0.5)
        child.parameters = {
            "temperature": float(f"{(t_a + t_b) / 2.0:.2f}"),
            "top_p": float(
                f"{(parent_a.parameters.get('top_p', 0.9) + parent_b.parameters.get('top_p', 0.9)) / 2:.2f}"
            ),
            "tools": list(
                set(parent_a.parameters.get("tools", [])).union(
                    set(parent_b.parameters.get("tools", []))
                )
            )[:5],
        }
        if random.random() < self.params.mutation_rate:
            shift = random.uniform(-0.1, 0.1) * (1.0 + self._endocrine.dopamine)
            child.parameters["temperature"] = max(
                0.01, min(1.0, float(f"{child.parameters['temperature'] + shift:.2f}"))
            )
        return child

    def _decision_archaeology(self, sovereign: SovereignAgent) -> None:
        """Analyze ledger to prune regressive lineages (Axioms Ω₁ + Ω₃)."""
        pruned_count = 0
        to_remove = []
        for sub in sovereign.subagents:
            history = self._evolution_ledger.get_mutation_history(sub.id, limit=5)
            if len(history) < 3:
                continue
            deltas = [h["delta_fitness"] for h in history]
            net_impact = sum(deltas)
            if net_impact < -5.0:
                logger.warning(
                    "Archaeology: Detected regressive lineage in %s (impact=%.1f). Amputating.",
                    sub.id,
                    net_impact,
                )
                to_remove.append(sub)
                pruned_count += 1
        for sub in to_remove:
            sovereign.subagents.remove(sub)
        if pruned_count > 0:
            for _ in range(pruned_count):
                spawn = SubAgent(
                    id=f"rev_{secrets.token_hex(4)}",
                    domain=sovereign.domain,
                    name=f"Revived-{sovereign.domain.name}",
                )
                sovereign.subagents.append(spawn)
