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

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.models import EpisodicSnapshot, MemoryEntry, MemoryEvent
from cortex.memory.working import WorkingMemoryL1

try:
    from cortex.memory.vector_store import VectorStoreL2
except ImportError:  # qdrant_client not installed
    VectorStoreL2 = None  # type: ignore[assignment,misc]

__all__ = [
    "AsyncEncoder",
    "CortexMemoryManager",
    "EpisodicSnapshot",
    "EventLedgerL3",
    "MemoryEntry",
    "MemoryEvent",
    "VectorStoreL2",
    "WorkingMemoryL1",
]
