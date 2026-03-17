"""Evolution Operations Mixin — genetic operators and adversarial processes."""
# pyright: reportAttributeAccessIssue=false

import asyncio
import logging
import random
import secrets
import sqlite3
from typing import TYPE_CHECKING

from cortex.extensions.evolution.action import SymbolicActionState
from cortex.extensions.evolution.agents import Mutation, MutationType, SovereignAgent, SubAgent
from cortex.extensions.evolution.cortex_metrics import DomainMetrics
from cortex.extensions.evolution.models import EvolutionMetric, EvolutionMutation
from cortex.extensions.evolution.strategies import DEFAULT_STRATEGIES

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.extensions.evolution.engine.ops")


class EvolutionOpsMixin:
    """Mixin for genetic operations, extinctions, and adversarial grounding."""

    def _apply_epigenetic_modulation(self) -> None:
        """Modulate mutation rate and selection pressure via DigitalEndocrine."""
        self.params.mutation_rate = max(0.05, min(0.4, 0.1 + (self._endocrine.dopamine * 0.2)))
        self.params.selection_pressure = max(0.1, min(0.6, 0.3 + (self._endocrine.cortisol * 0.3)))

    async def _evaluate_adversarial(self, metrics: dict[str, DomainMetrics]) -> None:
        """Ground agent fitness in real telemetry (350/100)."""
        for sovereign in getattr(self, "sovereigns", []):
            domain_telemetry = metrics.get(sovereign.domain)
            if not domain_telemetry:
                continue

            h_score = domain_telemetry.health_score * 70.0
            f_delta = domain_telemetry.fitness_delta * 6.0
            grounded_fitness = h_score + f_delta
            sovereign.fitness = (sovereign.fitness * 0.8) + (grounded_fitness * 0.2)

            for sub in sovereign.subagents:
                success_ratio = domain_telemetry.decision_success_rate
                sub_delta = (success_ratio - 0.5) * 10.0
                sub.fitness = max(0.1, sub.fitness + sub_delta)

    def _lateral_transfer(self) -> int:
        """Plásmidos: Transfer parameters from random best to random target."""
        if random.random() > self.params.lateral_transfer_rate:
            return 0

        all_subs = [s for sov in getattr(self, "sovereigns", []) for s in sov.subagents]
        if not all_subs:
            return 0
        best_sub = max(all_subs, key=lambda s: s.fitness)

        target_sov = random.choice(self.sovereigns)
        target_sub = random.choice(target_sov.subagents)

        key = random.choice(["temperature", "top_p", "tools"])
        target_sub.parameters[key] = best_sub.parameters.get(key)
        target_sub.apply_mutation(
            Mutation(
                mutation_type=MutationType.LATERAL_TRANSFER,
                description=f"Infected with {key} from {best_sub.id}",
                delta_fitness=0.5,
            )
        )
        return 1

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
        child = SubAgent(
            id=f"sub_{parent_a.domain.name.lower()}_gen{self.cycle_count}_"
            f"{random.randint(1000, 9999)}",
            domain=parent_a.domain,
            name=f"Hybrid-{parent_a.name[:4]}-{parent_b.name[:4]}",
            generation=max(parent_a.generation, parent_b.generation) + 1,
        )

        child.epigenetic_state = {
            "dopamine_bias": self._endocrine.dopamine,
            "cortisol_bias": self._endocrine.cortisol,
        }

        t_a = parent_a.parameters.get("temperature", 0.5)
        t_b = parent_b.parameters.get("temperature", 0.5)
        child.parameters = {
            "temperature": round((t_a + t_b) / 2.0, 2),
            "top_p": round(
                (parent_a.parameters.get("top_p", 0.9) + parent_b.parameters.get("top_p", 0.9)) / 2,
                2,
            ),
            "tools": list(
                set(parent_a.parameters.get("tools", []))
                | set(parent_b.parameters.get("tools", []))
            )[:5],
        }

        if random.random() < self.params.mutation_rate:
            shift = random.uniform(-0.1, 0.1) * (1.0 + self._endocrine.dopamine)
            child.parameters["temperature"] = max(
                0.01, min(1.0, round(child.parameters["temperature"] + shift, 2))
            )

        return child

    def _mass_extinction(self) -> int:
        """Mass extinction: cull bottom agents and replace with max-entropy spores."""
        culled = 0
        for sovereign in getattr(self, "sovereigns", []):
            subs = sorted(sovereign.subagents, key=lambda s: s.fitness)
            cull_limit = int(len(subs) * self.params.extinction_cull_rate)
            survivors = subs[cull_limit:]

            while len(survivors) < len(subs):
                spawn = SubAgent(id=f"chaos_{random.randint(100, 999)}", domain=sovereign.domain)
                spawn.parameters = {"temperature": 1.0, "top_p": 1.0}
                survivors.append(spawn)
                culled += 1
            sovereign.subagents = survivors
        return culled

    def _adjust_meta_parameters(self, avg_lagrangian: float = 0.0) -> None:
        """Adjust meta-fitness targets based on Lagrangian coherence."""
        sovereigns = getattr(self, "sovereigns", [])
        if not sovereigns:
            return
        avg_fitness = sum(s.fitness for s in sovereigns) / len(sovereigns)

        if avg_lagrangian < 0:
            self.params.mutation_rate *= 1.2
            self.params.selection_pressure = min(0.6, self.params.selection_pressure + 0.05)
        elif avg_lagrangian > 10.0:
            self.params.mutation_rate *= 0.9

        self.params.meta_fitness_score = avg_fitness

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

    async def _ouroboros_pruning(self) -> None:
        """Enforces Landauer's Razor: Pruning dead-weight projects."""
        if not self._ouroboros:
            return

        target = await asyncio.to_thread(self._ouroboros.identify_dead_weight)
        if target:
            logger.warning("Ouroboros: Amputating project %s due to high entropy.", target)
            await asyncio.to_thread(self._ouroboros.trigger_pruning, target)

            try:
                from cortex.routes.notch_ws import notch_hub

                if notch_hub:
                    self._broadcast_task = asyncio.create_task(
                        notch_hub.broadcast('{"command": "shockwave", "intensity": 1.0}')
                    )
                    self._broadcast_task.add_done_callback(lambda t: None)
            except ImportError:
                pass

            result = await asyncio.to_thread(self._ouroboros.measure_entropy)
            logger.info("Ouroboros: Pruning complete. New Entropy: %.4f", result["entropy_index"])

        sovereigns = getattr(self, "sovereigns", [])
        all_subs = [sub for sov in sovereigns for sub in sov.subagents]
        if all_subs:
            worst = min(all_subs, key=lambda s: s.fitness)
            for sov in sovereigns:
                if worst in sov.subagents:
                    sov.subagents.remove(worst)
                    logger.info("Ouroboros: Culled weakest subagent %s", worst.id)

    async def _process_sovereign(
        self, sovereign: SovereignAgent, metrics: dict[str, DomainMetrics]
    ) -> tuple[list[EvolutionMutation], list[EvolutionMutation], int, SymbolicActionState | None]:
        """Ω₀: Isolated processing for a single sovereign domain. Concurrency-safe."""
        sovereign._cycle_count += 1
        domain_grace = 0.0
        sovereign_muts_to_record = []
        sub_muts_to_record = []
        crossovers_count = 0

        # Agent Mutations
        for strategy in DEFAULT_STRATEGIES:
            mutation = strategy.evaluate_agent(sovereign)
            if mutation:
                prev_h = sovereign.state_hash
                sovereign.apply_mutation(mutation)
                domain_grace += mutation.delta_fitness

                p_mutation = EvolutionMutation(
                    agent_id=sovereign.id,
                    mutation_type=mutation.mutation_type.name,
                    prev_hash=prev_h,
                    new_hash=sovereign.state_hash,
                    delta_fitness=mutation.delta_fitness,
                    metrics=[
                        EvolutionMetric("fitness", sovereign.fitness),
                        EvolutionMetric("cycle", float(self.cycle_count)),
                    ],
                    metadata={
                        "description": mutation.description,
                        "tier": getattr(sovereign, "evolution_tier", "N/A"),
                    },
                )
                sovereign_muts_to_record.append(p_mutation)

                if mutation.epigenetic_tags.get("axiom_12_trigger"):
                    self._record_merkle_checkpoint(sovereign, mutation)

        # Subagent Mutations
        for sub in sovereign.subagents:
            for strategy in DEFAULT_STRATEGIES:
                mutation = strategy.evaluate_subagent(sub)
                if mutation:
                    prev_h_sub = sub.state_hash
                    sub.apply_mutation(mutation)
                    sub_grace = mutation.delta_fitness / 10.0
                    domain_grace += sub_grace

                    p_mutation = EvolutionMutation(
                        agent_id=sub.id,
                        mutation_type=mutation.mutation_type.name,
                        prev_hash=prev_h_sub,
                        new_hash=sub.state_hash,
                        delta_fitness=mutation.delta_fitness,
                        metrics=[
                            EvolutionMetric("fitness", sub.fitness),
                            EvolutionMetric("grace_contribution", sub_grace),
                        ],
                        metadata={
                            "description": mutation.description,
                            "parent_sovereign": sovereign.id,
                            "tier": getattr(sub, "evolution_tier", "N/A"),
                        },
                    )
                    sub_muts_to_record.append(p_mutation)

                    if mutation.epigenetic_tags.get("axiom_12_trigger"):
                        self._record_merkle_checkpoint(sub, mutation)

        self._decision_archaeology(sovereign)

        domain_telemetry = metrics.get(sovereign.domain)  # type: ignore[type-error]
        state = None
        if domain_telemetry:
            state = self._action_engine.compute_state(
                sovereign, domain_telemetry, grace_injection=domain_grace
            )

        # Crossover & Survival
        subs = sorted(sovereign.subagents, key=lambda s: s.fitness, reverse=True)
        elite = subs[:3]
        cull_count = max(1, int(len(subs) * getattr(self.params, "selection_pressure", 0.3)))
        survivors = subs[:-cull_count] if cull_count < len(subs) else subs[:1]

        new_generation = list(survivors)
        for _ in range(cull_count if cull_count < len(subs) else 0):
            if len(elite) >= 2:
                parent_a, parent_b = random.sample(elite, 2)
            else:
                parent_a, parent_b = elite[0], elite[0]
            child = self._crossover(parent_a, parent_b)
            new_generation.append(child)
            crossovers_count += 1

        sovereign.subagents = new_generation
        return sovereign_muts_to_record, sub_muts_to_record, crossovers_count, state
