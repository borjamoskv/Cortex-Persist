import logging
import time
from typing import Any

from cortex.agents.manifest import AgentManifest
from cortex.agents.memento_ledger import MementoLedger, MementoStage
from cortex.context.hiagent import HiAgent
from cortex.extensions.policy.memory_os import MemoryOS
from cortex.guards.exergy_guard import ExergyGuard, calculate_exergy
from cortex.memory.contradiction import ContradictionScanner

logger = logging.getLogger("cortex.specialists.memento")

def _default_manifest() -> AgentManifest:
    return AgentManifest(
        agent_id="memento_specialist",
        purpose=(
            "Orchestrates the crystallization of episodic traces into semantic facts. "
            "Manages subgoal persistence and memory consistency."
        ),
        tools_allowed=["memory_os", "ledger", "contradiction_scanner"],
        max_consecutive_errors=3,
    )

class MementoAgent:
    """
    Sovereign 'Memento' Specialist for Subgoal and Semantic Memory Management.
    
    Orchestrates the crystallization of episodic traces into semantic facts
    using a state-machine driven lifecycle with contradiction gating.
    """
    
    def __init__(self, manifest: AgentManifest | None = None, session_id: str = "default", exergy_threshold: float = 0.5, engine: Any | None = None):
        self.manifest = manifest or _default_manifest()
        self.session_id = session_id
        self.hi_agent = HiAgent(session_id=session_id)
        self.memory_os = MemoryOS(
            exergy_threshold=exergy_threshold,
            engine=engine,
        )
        self.ledger = MementoLedger(engine=engine)
        self.scanner = ContradictionScanner(engine=engine)
        self.exergy_guard = ExergyGuard()
        self.engine = engine

        self._initialized = False
        self._stage = MementoStage.BUFFERING
        self._last_tick_ts = time.time()
        self._tick_interval = 10.0  # Standard tick for memory consolidation

    async def initialize(self):
        """Initialize ledger and internal components."""
        if not self._initialized:
            await self.ledger.initialize()
            self._initialized = True
            logger.info("[Memento] Agent initialized for session %s", self.session_id)

    async def record_trace(self, action: str, observation: str):
        """Append a trace and update ledger state if exergy is sufficient."""
        # Ω₂: Filter extremely low-exergy noise (e.g. repetitive "ok", "thanks")
        trace_text = f"{action} {observation}"
        exergy_score = calculate_exergy(trace_text)
        
        if exergy_score < 0.1:
            logger.debug("[Memento] Skipping low-exergy trace (score: %.2f)", exergy_score)
            return

        self.hi_agent.add_trace(str(action), str(observation))
        
        # Use explicit string casting to satisfy linter
        summary_txt = f"{action}"[:30] if action else "empty"
        obs_txt = f"{observation}"[:50] if observation else "empty"

        await self.ledger.record_transition(
            session_id=self.session_id,
            trace_id=f"trace_{int(time.time())}",
            stage=MementoStage.BUFFERING,
            summary=f"Trace: {summary_txt}...",
            evidence=f"Observation: {obs_txt}...",
            exergy_delta=exergy_score * 0.01  # Scaled exergy for trace
        )

    async def tick(self):
        """Autonomous lifecycle unit: consolidating episodic noise into semantic signal."""
        if not self._initialized:
            await self.initialize()

        now = time.time()
        if now - self._last_tick_ts < self._tick_interval:
            return

        logger.info("[Memento] Starting consolation cycle for session %s", self.session_id)
        
        # 1. ANALYZING: Extraction and Conflict Check
        self._stage = MementoStage.ANALYZING
        crystal = await self.hi_agent.crystallize()
        if not crystal:
            logger.debug("[Memento] No traces to crystallize.")
            self._stage = MementoStage.BUFFERING
            return

        # 2. CRYSTALLIZING: Semantic Gating
        self._stage = MementoStage.CRYSTALLIZED
        trace_id = f"crystal_{int(now)}"
        
        # SCAN for contradictions
        conflicts = await self.scanner.scan(crystal)
        if conflicts:
            logger.warning("[Memento] CONTRADICTION DETECTED. Reverting to quarantine.")
            await self.ledger.record_transition(
                session_id=self.session_id,
                trace_id=trace_id,
                stage=MementoStage.REJECTED,
                summary="Crystallization Rejected",
                evidence=f"Detected {len(conflicts)} contradictions with existing memory.",
                extra={"conflicts": conflicts}
            )
            self._stage = MementoStage.BUFFERING
            return

        # 3. PERSISTING: Thermodynamic Write
        self._stage = MementoStage.PERSISTED
        res = await self.memory_os.persist_episodic_to_semantic(crystal)
        stored_count = int(res) if res else 0
        
        # CALCULATE EXERGY (Ω₉)
        exergy_val = await self.exergy_guard.calculate_proposal_exergy({
            "facts": crystal,
            "session_id": self.session_id,
            "stored_count": stored_count
        })

        # Record final persistence
        await self.ledger.record_transition(
            session_id=self.session_id,
            trace_id=trace_id,
            stage=MementoStage.PERSISTED,
            summary=f"Stored {stored_count} facts",
            exergy_delta=exergy_val,
            hours_saved=float(stored_count) * 0.5, # CHRONOS-1: 30 mins saved per crystallized fact
            evidence=f"Successfully persisted to L3 Ledger. Exergy: {exergy_val:.4f}"
        )

        self._last_tick_ts = now
        self._stage = MementoStage.BUFFERING
        logger.info("[Memento] Consolidation complete. Stored %d facts.", stored_count)

    async def run_maintenance(self):
        """Execute periodic thermodynamic garbage collection."""
        logger.info("[Memento] Running thermodynamic maintenance (GC)")
        await self.memory_os.gc()
        await self.ledger.record_transition(
            session_id=self.session_id,
            trace_id="gc_cycle",
            stage=MementoStage.GC,
            summary="Thermodynamic Maintenance",
            evidence="Pruned historical exergy debt from memory OS."
        )

    async def recall(self, query: str, limit: int = 5) -> list[dict]:
        """Ω₉: Semantic archaeology. Retrieve stored facts for the current session."""
        if not self._initialized:
            await self.initialize()
        return await self.ledger.semantic_search(query, session_id=self.session_id, limit=limit)

    async def compact(self):
        """Ω₄: Shannon Compaction. Prunes low-exergy noise and merges duplicates."""
        logger.info("[Memento] Running Shannon Compaction for session %s", self.session_id)

        pruned = await self.ledger.prune_low_exergy(session_id=self.session_id)
        merged = await self.ledger.merge_duplicates(session_id=self.session_id)

        await self.ledger.record_transition(
            session_id=self.session_id,
            trace_id="compaction_cycle",
            stage=MementoStage.ANALYZING,
            summary="Shannon Compaction",
            evidence=(
                f"Pruned {pruned} low-exergy traces, "
                f"merged {merged} duplicates."
            ),
        )

    @property
    def stage(self) -> MementoStage:
        return self._stage

    async def shutdown(self):
        """Shutdown components and close database pools."""
        if self._initialized:
            await self.ledger.shutdown()
            self._initialized = False
            logger.info("[Memento] Agent shutdown for session %s", self.session_id)

    async def get_stats(self) -> dict:
        """Retrieve ledger statistics."""
        return await self.ledger.get_stats()

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search crystallized memory via semantic context."""
        return await self.ledger.semantic_search(query, limit=limit)
