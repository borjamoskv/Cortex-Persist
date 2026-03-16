import asyncio
import logging
import secrets
import time
from pathlib import Path
from typing import Any

from cortex.database.core import connect as db_connect
from cortex.evolution.action import SymbolicActionEngine
from cortex.evolution.agents import (
    AgentDomain,
    SovereignAgent,
    SubAgent,
)
from cortex.evolution.cortex_metrics import fetch_all_domain_metrics
from cortex.evolution.ledger_db import EvolutionLedgerDB
from cortex.evolution.lnn import LagrangianController
from cortex.evolution.models import (
    CycleReport,
    EngineParameters,
)
from cortex.evolution.operations_mixin import EvolutionOpsMixin
from cortex.evolution.persistence import load_swarm, save_swarm
from cortex.gate.ouroboros import OuroborosGate
from cortex.ledger import SovereignLedger
from cortex.sovereign.endocrine import DigitalEndocrine

random = secrets.SystemRandom()

logger = logging.getLogger("cortex.evolution.engine")


class EvolutionEngine(EvolutionOpsMixin):
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
        await self._evaluate_adversarial(metrics)  # type: ignore[type-error]

        # 4. Extinción Masiva
        if self.cycle_count % self.params.extinction_cycle == 0:
            if random.random() > 0.5:
                await self._ouroboros_pruning()
                extinctions = 1
            else:
                extinctions = self._mass_extinction()

        # 5. Selección, Recombinación y Plásmidos (Ω₀ Parallelized)
        tasks = [self._process_sovereign(s, metrics) for s in self.sovereigns]  # type: ignore[type-error]
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
