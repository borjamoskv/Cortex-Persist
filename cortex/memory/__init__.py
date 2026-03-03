"""
CORTEX v5.3 — Cognitive Memory Module.

Tripartite Memory Architecture (KETER-∞ Frontera 2):
    L1: WorkingMemoryL1  — Token-budgeted sliding window
    L2: VectorStoreL2    — Qdrant-backed semantic recall
    L3: EventLedgerL3    — SQLite WAL immutable event log

Orchestrator: CortexMemoryManager wires L1 → L2 → L3.

Usage::

    from cortex.memory import CortexMemoryManager, WorkingMemoryL1

"""

from cortex.memory.consolidation import SilentEngram, SystemsConsolidator
from cortex.memory.drift import DriftMonitor, DriftSignature
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.engrams import CortexSemanticEngram
from cortex.memory.frequency import (
    BIFTRouter,
    ContinuousMemorySystem,
    MemoryFrequency,
    RetrievalBand,
)
from cortex.memory.homeostasis import DynamicSynapseUpdate, EntropyPruner
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.metamemory import (
    MemoryCard,
    MetacognitiveJudge,
    MetaJudgment,
    MetamemoryIndex,
    MetamemoryMonitor,
    MetamemoryStats,
    RetrievalOutcome,
    Verdict,
    build_memory_card,
)
from cortex.memory.models import EpisodicSnapshot, MemoryEntry, MemoryEvent
from cortex.memory.sleep import SleepCycleReport, SleepOrchestrator
from cortex.memory.navigator import (
    ClusterInfo,
    KnowledgeMap,
    NavigationState,
    SemanticNavigator,
    SemanticPath,
)
from cortex.memory.resonance import AdaptiveResonanceGate
from cortex.memory.sparse import MushroomBodyEncoder
from cortex.memory.temporal_health import (
    HealthReport,
    SchedulerConfig,
    TemporalHealthScheduler,
)
from cortex.memory.void_detector import (
    EpistemicAnalysis,
    EpistemicState,
    EpistemicVoidDetector,
)
from cortex.memory.pipeline import NeuromorphicPipeline, QueryResult, StoreResult
from cortex.memory.working import WorkingMemoryL1

try:
    from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

    VectorStoreL2 = SovereignVectorStoreL2
except ImportError:
    try:
        from cortex.memory.vector_store import (
            VectorStoreL2,  # type: ignore[import-not-found,reportMissingImports]
        )
    except ImportError:
        VectorStoreL2 = None  # type: ignore[assignment,misc]

__all__ = [
    "AdaptiveResonanceGate",
    "AsyncEncoder",
    "BIFTRouter",
    "ContinuousMemorySystem",
    "CortexMemoryManager",
    "ClusterInfo",
    "CortexSemanticEngram",
    "DriftMonitor",
    "DriftSignature",
    "DynamicSynapseUpdate",
    "EntropyPruner",
    "EpistemicAnalysis",
    "EpistemicState",
    "EpistemicVoidDetector",
    "EpisodicSnapshot",
    "EventLedgerL3",
    "HealthReport",
    "MemoryCard",
    "KnowledgeMap",
    "MemoryEntry",
    "MemoryEvent",
    "MemoryFrequency",
    "MetaJudgment",
    "MetacognitiveJudge",
    "MetamemoryIndex",
    "MetamemoryMonitor",
    "MetamemoryStats",
    "MushroomBodyEncoder",
    "NavigationState",
    "NeuromorphicPipeline",
    "QueryResult",
    "RetrievalBand",
    "RetrievalOutcome",
    "SchedulerConfig",
    "SemanticNavigator",
    "SemanticPath",
    "SilentEngram",
    "SleepCycleReport",
    "SleepOrchestrator",
    "StoreResult",
    "SystemsConsolidator",
    "TemporalHealthScheduler",
    "VectorStoreL2",
    "Verdict",
    "WorkingMemoryL1",
    "build_memory_card",
]
