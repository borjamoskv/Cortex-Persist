import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

from cortex.evolution.agents import (
    AgentDomain,
    Mutation,
    MutationType,
    SovereignAgent,
    SubAgent,
)
from cortex.evolution.cortex_metrics import DomainMetrics, fetch_all_domain_metrics
from cortex.evolution.persistence import load_swarm, save_swarm
from cortex.gate.ouroboros import OuroborosGate
from cortex.sovereign.endocrine import DigitalEndocrine

logger = logging.getLogger("cortex.evolution.engine")


@dataclass
class CycleReport:
    """Metrics produced at the end of a single evolutionary cycle."""

    cycle: int
    avg_agent_fitness: float
    best_agent_fitness: float
    worst_agent_fitness: float
    avg_subagent_fitness: float
    total_mutations: int
    tournaments_run: int
    species_count: int
    duration_ms: float
    crossovers: int = 0
    extinctions: int = 0


@dataclass
class EngineParameters:
    """Hyperparameters for the Evolution Engine (Meta-Fitness targets)."""

    selection_pressure: float = 0.3
    mutation_rate: float = 0.1
    extinction_cycle: int = 10
    extinction_cull_rate: float = 0.5
    speciation_rate: float = 0.1
    lateral_transfer_rate: float = 0.15  # 350/100: Lateral Transfer
    meta_fitness_score: float = 0.0


class EvolutionEngine:
    """The thermodynamic singularity driving CORTEX adaptation.

    Phase 6 Implementation (Singularity):
    - Full Async Orchestration
    - Lateral Transfer (Plásmidos)
    - Epigenetic Modulation (Endocrine)
    - Adversarial Grounding (Telemetry)
    """

    def __init__(self, sovereigns: list[SovereignAgent] | None = None, engine: Any | None = None):
        self.sovereigns = sovereigns or []
        self.params = EngineParameters()
        self.cycle_count = 0
        self.last_run: float = 0.0
        self.engine = engine
        self._ouroboros = None
        self._endocrine = DigitalEndocrine()  # 350/100 Integration
        if self.engine:
            self._ouroboros = OuroborosGate(self.engine._get_sync_conn())

    async def initialize_swarm(self) -> None:
        """Load from disk or create genesis swarm (Async)."""
        # persistence might be sync for now, wrapping in thread if needed
        loaded = await asyncio.to_thread(load_swarm)
        if loaded:
            agents, cycle = loaded
            self.sovereigns = agents
            self.cycle_count = cycle
            logger.info("Loaded evolutionary swarm at cycle %d", cycle)
        else:
            logger.info("No valid state found. Initializing genesis swarm.")
            self._create_genesis_swarm()

    def _create_genesis_swarm(self) -> None:
        """Create the 10 domain sovereigns with 10 subagents each."""
        self.sovereigns = []
        for domain in AgentDomain:
            if domain == AgentDomain.SYNERGY:
                continue
            sovereign = SovereignAgent(id=f"sov_{domain.name.lower()}", domain=domain)
            sovereign.subagents.clear()

            for i in range(10):
                sub = SubAgent(
                    id=f"sub_{domain.name.lower()}_{i:02d}",
                    domain=domain,
                    name=f"Genesis-{domain.name}-{i:02d}",
                )
                sub.parameters = {
                    "temperature": round(random.uniform(0.1, 1.0), 2),
                    "top_p": round(random.uniform(0.8, 1.0), 2),
                    "system_prompt": f"You are a specialized agent for {domain.name}.",
                    "tools": ["search", "read"] if random.random() > 0.5 else ["write", "execute"],
                }
                sovereign.subagents.append(sub)
            self.sovereigns.append(sovereign)

    async def cycle(self) -> CycleReport:
        """Execute one full evolutionary cycle (Async 350/100)."""
        start_time = time.time()
        self.cycle_count += 1

        crossovers = 0
        extinctions = 0
        transfers = 0

        # 1. Fetch Terminal Metrics (Afferent snapshot)
        metrics = await fetch_all_domain_metrics()

        # 2. Epigenetic Modulation (Endocrine feedback)
        self._apply_epigenetic_modulation()

        # 3. Torneo Adversarial (Telemetry-Grounding)
        await self._evaluate_adversarial(metrics)

        # 4. Extinción Masiva
        if self.cycle_count % self.params.extinction_cycle == 0:
            # 350/100: Ouroboros Pruning takes precedence over random extinction
            if random.random() > 0.5:
                await self._ouroboros_pruning()
                extinctions = 1
            else:
                extinctions = self._mass_extinction()

        # 5. Selección, Recombinación y Plásmidos
        for sovereign in self.sovereigns:
            sovereign._cycle_count += 1
            subs = sorted(sovereign.subagents, key=lambda s: s.fitness, reverse=True)
            elite = subs[:3]
            cull_count = max(1, int(len(subs) * self.params.selection_pressure))
            survivors = subs[:-cull_count]

            new_generation = list(survivors)

            for _ in range(cull_count):
                parent_a, parent_b = random.sample(elite, 2)
                child = self._crossover(parent_a, parent_b)
                new_generation.append(child)
                crossovers += 1

            sovereign.subagents = new_generation

        # 6. Lateral Transfer (Plásmidos) - Cross-domain infection
        transfers = self._lateral_transfer()

        # 7. Meta-Fitness / Optimization
        self._adjust_meta_parameters()

        # 8. Persistence (Async-Thread)
        await asyncio.to_thread(save_swarm, self.sovereigns, self.cycle_count)

        self.last_run = time.time()
        duration_ms = (self.last_run - start_time) * 1000

        # Population Metrics
        all_subs = [sub for sov in self.sovereigns for sub in sov.subagents]
        avg_sub_fitness = sum(s.fitness for s in all_subs) / max(1, len(all_subs))

        logger.info(
            "Singularity Cycle %d complete: %d crossovers, %d extinctions, %d transfers in %.0fms",
            self.cycle_count,
            crossovers,
            extinctions,
            transfers,
            duration_ms,
        )

        return CycleReport(
            cycle=self.cycle_count,
            avg_agent_fitness=sum(s.fitness for s in self.sovereigns) / len(self.sovereigns),
            best_agent_fitness=max(s.fitness for s in self.sovereigns),
            worst_agent_fitness=min(s.fitness for s in self.sovereigns),
            avg_subagent_fitness=avg_sub_fitness,
            total_mutations=sum(len(s.mutations) for s in all_subs),
            tournaments_run=len(all_subs),
            species_count=len(self.sovereigns),
            duration_ms=duration_ms,
            crossovers=crossovers,
            extinctions=extinctions,
        )

    def _apply_epigenetic_modulation(self) -> None:
        """Modulate mutation parameters based on DigitalEndocrine state."""
        # High dopamine increases mutation variance
        # High cortisol favors pruning/conservative states
        self.params.mutation_rate = max(0.05, min(0.4, 0.1 + (self._endocrine.dopamine * 0.2)))
        self.params.selection_pressure = max(0.1, min(0.6, 0.3 + (self._endocrine.cortisol * 0.3)))

    async def _evaluate_adversarial(self, metrics: dict[AgentDomain, DomainMetrics]) -> None:
        """Ground agent fitness in real telemetry (350/100)."""
        for sovereign in self.sovereigns:
            domain_telemetry = metrics.get(sovereign.domain)
            if not domain_telemetry:
                continue

            # δ_fitness = (health * 0.7) + (delta * 0.3)
            h_score = domain_telemetry.health_score * 70.0
            f_delta = domain_telemetry.fitness_delta * 6.0
            grounded_fitness = h_score + f_delta

            # Smooth update
            sovereign.fitness = (sovereign.fitness * 0.8) + (grounded_fitness * 0.2)

            # Apply to subagents (proportional to their temp stability)
            for sub in sovereign.subagents:
                success_ratio = domain_telemetry.decision_success_rate
                sub_delta = (success_ratio - 0.5) * 10.0
                sub.fitness = max(0.1, sub.fitness + sub_delta)

    def _lateral_transfer(self) -> int:
        """Plásmidos: Transfer parameters from the global best subagent to a random domain."""
        if random.random() > self.params.lateral_transfer_rate:
            return 0

        all_subs = [s for sov in self.sovereigns for s in sov.subagents]
        best_sub = max(all_subs, key=lambda s: s.fitness)

        target_sov = random.choice(self.sovereigns)
        target_sub = random.choice(target_sov.subagents)

        # Infect parameters
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

    def _crossover(self, parent_a: SubAgent, parent_b: SubAgent) -> SubAgent:
        child = SubAgent(
            id=f"sub_{parent_a.domain.name.lower()}_gen{self.cycle_count}_"
            f"{random.randint(1000, 9999)}",
            domain=parent_a.domain,
            name=f"Hybrid-{parent_a.name[:4]}-{parent_b.name[:4]}",
            generation=max(parent_a.generation, parent_b.generation) + 1,
        )

        # Epigenetic Inheritance
        child.epigenetic_state = {
            "dopamine_bias": self._endocrine.dopamine,
            "cortisol_bias": self._endocrine.cortisol,
        }

        # Parameters
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

        # Mutation
        if random.random() < self.params.mutation_rate:
            shift = random.uniform(-0.1, 0.1) * (1.0 + self._endocrine.dopamine)
            child.parameters["temperature"] = max(
                0.01, min(1.0, round(child.parameters["temperature"] + shift, 2))
            )

        return child

    def _mass_extinction(self) -> int:
        culled = 0
        for sovereign in self.sovereigns:
            subs = sorted(sovereign.subagents, key=lambda s: s.fitness)
            cull_limit = int(len(subs) * self.params.extinction_cull_rate)
            survivors = subs[cull_limit:]

            while len(survivors) < len(subs):
                # Replace with max-entropy spawns
                spawn = SubAgent(id=f"chaos_{random.randint(100, 999)}", domain=sovereign.domain)
                spawn.parameters = {"temperature": 1.0, "top_p": 1.0}
                survivors.append(spawn)
                culled += 1
            sovereign.subagents = survivors
        return culled

    def _adjust_meta_parameters(self) -> None:
        avg_fitness = sum(s.fitness for s in self.sovereigns) / len(self.sovereigns)
        if avg_fitness > self.params.meta_fitness_score:
            self.params.mutation_rate *= 0.95
        else:
            self.params.mutation_rate *= 1.1
        self.params.meta_fitness_score = avg_fitness

    async def _ouroboros_pruning(self) -> None:
        """Enforces Landauer's Razor: Pruning dead-weight projects."""
        if not self._ouroboros:
            return

        target = await asyncio.to_thread(self._ouroboros.identify_dead_weight)
        if target:
            logger.warning("Ouroboros: Amputating project %s due to high entropy.", target)
            await asyncio.to_thread(self._ouroboros.trigger_pruning, target)

            # 350/100: Visual Feedback via Notch Live
            from cortex.routes.notch_ws import notch_hub

            if notch_hub:
                # Persistent reference to avoid garbage collection
                self._broadcast_task = asyncio.create_task(
                    notch_hub.broadcast('{"command": "shockwave", "intensity": 1.0}')
                )

            # Recompute entropy index (wrapped in thread to avoid blocking)
            result = await asyncio.to_thread(self._ouroboros.measure_entropy)
            logger.info(
                "Ouroboros: Pruning complete. New Entropy Index: %.4f", result["entropy_index"]
            )

        # Cull weakest subagents globally
        all_subs = [sub for sov in self.sovereigns for sub in sov.subagents]
        if all_subs:
            worst = min(all_subs, key=lambda s: s.fitness)
            for sov in self.sovereigns:
                if worst in sov.subagents:
                    sov.subagents.remove(worst)
                    logger.info("Ouroboros: Culled weakest subagent %s", worst.id)
