import asyncio
import logging
import secrets
import time
from pathlib import Path
from typing import Any

from cortex.database.core import connect as db_connect
from cortex.evolution.action import SymbolicActionEngine, SymbolicActionState
from cortex.evolution.agents import (
    AgentDomain,
    Mutation,
    MutationType,
    SovereignAgent,
    SubAgent,
)
from cortex.evolution.cortex_metrics import DomainMetrics, fetch_all_domain_metrics
from cortex.evolution.ledger_db import EvolutionLedgerDB
from cortex.evolution.lnn import LagrangianController
from cortex.evolution.models import (
    CycleReport,
    EngineParameters,
    EvolutionMetric,
    EvolutionMutation,
)
from cortex.evolution.persistence import load_swarm, save_swarm
from cortex.evolution.strategies import DEFAULT_STRATEGIES
from cortex.gate.ouroboros import OuroborosGate
from cortex.ledger import SovereignLedger
from cortex.sovereign.endocrine import DigitalEndocrine

random = secrets.SystemRandom()

logger = logging.getLogger("cortex.evolution.engine")


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
        self._endocrine = DigitalEndocrine()
        self._action_engine = SymbolicActionEngine()
        self._lnn = LagrangianController()
        self._ledger = self._build_ledger()
        self._evolution_ledger = EvolutionLedgerDB()
        if self.engine:
            self._ouroboros = OuroborosGate(self.engine._get_sync_conn())

    def _build_ledger(self) -> SovereignLedger:
        """Build a persistent SovereignLedger for evolution checkpoints."""
        ledger_path = Path("~/.cortex/evolution_ledger.db").expanduser()
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        conn = db_connect(str(ledger_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        return SovereignLedger(conn)

    async def initialize_swarm(self) -> None:
        """Load from disk or create genesis swarm (Async)."""
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
        """Execute one full evolutionary cycle (Async 350/100).

        The core thermodynamic pump of the singularity pipeline.
        Orchestrates an atomic generation leap via:
        1. Afferent Telemetry (Fetching survival vectors)
        2. Epigenetic Transcription (Cortisol/Dopamine modulation)
        3. Adversarial Grounding (Telemetry validation of fitness functions)
        4. Ouroboros Pruning / Mass Extinction (Entropy reduction)
        5. Sovereign Processing (Evaluation, Selection, and Crossover)
        6. Lateral Merkle Transfers (Plasmids)

        Returns:
            CycleReport: Telemetry and generation delta metrics.
        """
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
            if random.random() > 0.5:
                await self._ouroboros_pruning()
                extinctions = 1
            else:
                extinctions = self._mass_extinction()

        # 5. Selección, Recombinación y Plásmidos (Ω₀ Parallelized)
        tasks = [self._process_sovereign(s, metrics) for s in self.sovereigns]
        results = await asyncio.gather(*tasks)

        all_mutations = []
        domain_states = {}
        crossovers = 0
        total_grace = 0.0

        for sovereign_muts, domain_muts, crossovers_count, domain_state in results:
            all_mutations.extend(sovereign_muts)
            all_mutations.extend(domain_muts)
            crossovers += crossovers_count
            total_grace += sum(m.delta_fitness for m in sovereign_muts)
            total_grace += sum(m.delta_fitness for m in domain_muts)
            if domain_state:
                domain_states[domain_state.domain] = domain_state

        # Batch record all mutations in one pass
        if all_mutations:
            self._evolution_ledger.record_mutations_batch(all_mutations)

        transfers = self._lateral_transfer()

        avg_lagrangian = 0.0
        if domain_states:
            avg_lagrangian = sum(s.lagrangian for s in domain_states.values()) / len(domain_states)
        self._adjust_meta_parameters(avg_lagrangian)

        self._save_task = asyncio.create_task(
            asyncio.to_thread(save_swarm, self.sovereigns, self.cycle_count)
        )

        self.last_run = time.time()
        duration_ms = (self.last_run - start_time) * 1000

        all_subs = [sub for sov in self.sovereigns for sub in sov.subagents]
        pop_size = len(all_subs)
        avg_sub_fitness = sum(s.fitness for s in all_subs) / max(1, pop_size)

        logger.info(
            "Singularity Cycle %d: C:%d E:%d T:%d | %.0fms",
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
            grace_injection=total_grace,
            lagrangian_index=avg_lagrangian,
        )

    def _apply_epigenetic_modulation(self) -> None:
        """Modulate mutation rate and selection pressure via DigitalEndocrine.

        Dopamine scaling increases the risk tolerance (mutation_rate), simulating
        reward-driven exploration. High Cortisol scales selection pressure,
        triggering aggressive culling during stressful runtime states.
        """
        self.params.mutation_rate = max(0.05, min(0.4, 0.1 + (self._endocrine.dopamine * 0.2)))
        self.params.selection_pressure = max(0.1, min(0.6, 0.3 + (self._endocrine.cortisol * 0.3)))

    async def _evaluate_adversarial(self, metrics: dict[AgentDomain, DomainMetrics]) -> None:
        """Ground agent fitness in real telemetry (350/100)."""
        for sovereign in self.sovereigns:
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

        all_subs = [s for sov in self.sovereigns for s in sov.subagents]
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
        except Exception as exc:
            logger.warning("Ledger write failed for agent %s: %s", agent.id, exc)

        agent.mutations.clear()

    def _crossover(self, parent_a: SubAgent, parent_b: SubAgent) -> SubAgent:
        """Perform genetic crossover combining two parent SubAgents into a new offspring.

        The hybrid offspring inherits the averaged system parameters (Temperature, Top P),
        a synthesized intersection of tool access, and the epigenetic biases spanning
        the generation. The child's mutation parameters are also smeared probabilistically.

        Args:
            parent_a (SubAgent): The primary elite parent.
            parent_b (SubAgent): The secondary elite parent.

        Returns:
            SubAgent: The emergent hybrid genome ready for adversarial grinding.
        """
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
        """Simulate a mass extinction event by culling a large percentage of populations.

        Eliminates subagents unconditionally using the bottom threshold of their
        fitness distributions (`extinction_cull_rate`). Replenishes the void with
        maximum-entropy 'chaos' spores (Temp=1.0) to jumpstart isolated genetic diversity.

        Returns:
            int: Number of specimens eradicated across all domains.
        """
        culled = 0
        for sovereign in self.sovereigns:
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
        """Adjust meta-fitness targets based on Lagrangian coherence (Phase 2 v3).

        If the swarm exhibits divergent behavior (`avg_lagrangian` < 0), selection pressure
        and mutation rates are throttled up to enforce convergence. If the system hyper-converges
        (high structural similarity, >10.0), mutation is drastically lowered to secure efficiency.

        Args:
            avg_lagrangian (float): The mean structural inertia coherence vector.
        """
        avg_fitness = sum(s.fitness for s in self.sovereigns) / len(self.sovereigns)

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

            from cortex.routes.notch_ws import notch_hub

            if notch_hub:
                self._broadcast_task = asyncio.create_task(
                    notch_hub.broadcast('{"command": "shockwave", "intensity": 1.0}')
                )

            result = await asyncio.to_thread(self._ouroboros.measure_entropy)
            logger.info("Ouroboros: Pruning complete. New Entropy: %.4f", result["entropy_index"])

        all_subs = [sub for sov in self.sovereigns for sub in sov.subagents]
        if all_subs:
            worst = min(all_subs, key=lambda s: s.fitness)
            for sov in self.sovereigns:
                if worst in sov.subagents:
                    sov.subagents.remove(worst)
                    logger.info("Ouroboros: Culled weakest subagent %s", worst.id)

    async def _process_sovereign(
        self, sovereign: SovereignAgent, metrics: dict[AgentDomain, DomainMetrics]
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
                            "tier": sub.evolution_tier,
                        },
                    )
                    sub_muts_to_record.append(p_mutation)

                    if mutation.epigenetic_tags.get("axiom_12_trigger"):
                        self._record_merkle_checkpoint(sub, mutation)

        self._decision_archaeology(sovereign)

        domain_telemetry = metrics.get(sovereign.domain)
        state = None
        if domain_telemetry:
            state = self._action_engine.compute_state(
                sovereign, domain_telemetry, grace_injection=domain_grace
            )

        # Crossover & Survival
        subs = sorted(sovereign.subagents, key=lambda s: s.fitness, reverse=True)
        elite = subs[:3]
        cull_count = max(1, int(len(subs) * self.params.selection_pressure))
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
