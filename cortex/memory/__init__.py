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
from cortex.memory.models import EpisodicSnapshot, MemoryEntry, MemoryEvent
from cortex.memory.resonance import AdaptiveResonanceGate
from cortex.memory.sparse import MushroomBodyEncoder
from cortex.memory.working import WorkingMemoryL1

try:
    from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

    VectorStoreL2 = SovereignVectorStoreL2
except ImportError:
    try:
        from cortex.memory.vector_store import VectorStoreL2
    except ImportError:
        VectorStoreL2 = None  # type: ignore[assignment,misc]

__all__ = [
    "AdaptiveResonanceGate",
    "AsyncEncoder",
    "BIFTRouter",
    "ContinuousMemorySystem",
    "CortexMemoryManager",
    "CortexSemanticEngram",
    "DynamicSynapseUpdate",
    "EntropyPruner",
    "EpisodicSnapshot",
    "EventLedgerL3",
    "MemoryEntry",
    "MemoryEvent",
    "MemoryFrequency",
    "MushroomBodyEncoder",
    "RetrievalBand",
    "SilentEngram",
    "SystemsConsolidator",
    "VectorStoreL2",
    "WorkingMemoryL1",
]
