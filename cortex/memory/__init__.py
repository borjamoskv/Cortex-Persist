"""
CORTEX v5.3 — Cognitive Memory Module.

Tripartite Memory Architecture (KETER-∞ Frontera 2):
    L1: WorkingMemoryL1  — Token-budgeted sliding window
    L2: VectorStoreL2    — Qdrant-backed semantic recall
    L3: EventLedgerL3    — SQLite WAL immutable event log

Orchestrator: CortexMemoryManager wires L1 → L2 → L3.

Uses __getattr__ lazy loading to avoid pulling in 18 submodules
eagerly on package import (PEP 562).

Usage::

    from cortex.memory import CortexMemoryManager, WorkingMemoryL1

"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.memory.consolidation import SilentEngram as SilentEngram
    from cortex.memory.consolidation import SystemsConsolidator as SystemsConsolidator
    from cortex.memory.drift import DriftMonitor as DriftMonitor
    from cortex.memory.drift import DriftSignature as DriftSignature
    from cortex.memory.encoder import AsyncEncoder as AsyncEncoder
    from cortex.memory.engrams import CortexSemanticEngram as CortexSemanticEngram
    from cortex.memory.frequency import BIFTRouter as BIFTRouter
    from cortex.memory.frequency import ContinuousMemorySystem as ContinuousMemorySystem
    from cortex.memory.frequency import MemoryFrequency as MemoryFrequency
    from cortex.memory.frequency import RetrievalBand as RetrievalBand
    from cortex.memory.homeostasis import DynamicSynapseUpdate as DynamicSynapseUpdate
    from cortex.memory.homeostasis import EntropyPruner as EntropyPruner
    from cortex.memory.ledger import EventLedgerL3 as EventLedgerL3
    from cortex.memory.manager import CortexMemoryManager as CortexMemoryManager
    from cortex.memory.metamemory import MemoryCard as MemoryCard
    from cortex.memory.metamemory import MetacognitiveJudge as MetacognitiveJudge
    from cortex.memory.metamemory import MetaJudgment as MetaJudgment
    from cortex.memory.metamemory import MetamemoryIndex as MetamemoryIndex
    from cortex.memory.metamemory import MetamemoryMonitor as MetamemoryMonitor
    from cortex.memory.metamemory import MetamemoryStats as MetamemoryStats
    from cortex.memory.metamemory import RetrievalOutcome as RetrievalOutcome
    from cortex.memory.metamemory import Verdict as Verdict
    from cortex.memory.metamemory import build_memory_card as build_memory_card
    from cortex.memory.models import EpisodicSnapshot as EpisodicSnapshot
    from cortex.memory.models import MemoryEntry as MemoryEntry
    from cortex.memory.models import MemoryEvent as MemoryEvent
    from cortex.memory.navigator import ClusterInfo as ClusterInfo
    from cortex.memory.navigator import KnowledgeMap as KnowledgeMap
    from cortex.memory.navigator import NavigationState as NavigationState
    from cortex.memory.navigator import SemanticNavigator as SemanticNavigator
    from cortex.memory.navigator import SemanticPath as SemanticPath
    from cortex.memory.pipeline import NeuromorphicPipeline as NeuromorphicPipeline
    from cortex.memory.pipeline import QueryResult as QueryResult
    from cortex.memory.pipeline import StoreResult as StoreResult
    from cortex.memory.resonance import AdaptiveResonanceGate as AdaptiveResonanceGate
    from cortex.memory.sleep import SleepCycleReport as SleepCycleReport
    from cortex.memory.sleep import SleepOrchestrator as SleepOrchestrator
    from cortex.memory.sparse import MushroomBodyEncoder as MushroomBodyEncoder
    from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2 as VectorStoreL2
    from cortex.memory.temporal_health import HealthReport as HealthReport
    from cortex.memory.temporal_health import SchedulerConfig as SchedulerConfig
    from cortex.memory.temporal_health import TemporalHealthScheduler as TemporalHealthScheduler
    from cortex.memory.void_detector import EpistemicAnalysis as EpistemicAnalysis
    from cortex.memory.void_detector import EpistemicState as EpistemicState
    from cortex.memory.void_detector import EpistemicVoidDetector as EpistemicVoidDetector
    from cortex.memory.working import WorkingMemoryL1 as WorkingMemoryL1

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

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # consolidation
    "SilentEngram": ("cortex.memory.consolidation", "SilentEngram"),
    "SystemsConsolidator": ("cortex.memory.consolidation", "SystemsConsolidator"),
    # drift
    "DriftMonitor": ("cortex.memory.drift", "DriftMonitor"),
    "DriftSignature": ("cortex.memory.drift", "DriftSignature"),
    # encoder
    "AsyncEncoder": ("cortex.memory.encoder", "AsyncEncoder"),
    # engrams
    "CortexSemanticEngram": ("cortex.memory.engrams", "CortexSemanticEngram"),
    # frequency
    "BIFTRouter": ("cortex.memory.frequency", "BIFTRouter"),
    "ContinuousMemorySystem": ("cortex.memory.frequency", "ContinuousMemorySystem"),
    "MemoryFrequency": ("cortex.memory.frequency", "MemoryFrequency"),
    "RetrievalBand": ("cortex.memory.frequency", "RetrievalBand"),
    # homeostasis
    "DynamicSynapseUpdate": ("cortex.memory.homeostasis", "DynamicSynapseUpdate"),
    "EntropyPruner": ("cortex.memory.homeostasis", "EntropyPruner"),
    # ledger
    "EventLedgerL3": ("cortex.memory.ledger", "EventLedgerL3"),
    # manager
    "CortexMemoryManager": ("cortex.memory.manager", "CortexMemoryManager"),
    # metamemory
    "MemoryCard": ("cortex.memory.metamemory", "MemoryCard"),
    "MetacognitiveJudge": ("cortex.memory.metamemory", "MetacognitiveJudge"),
    "MetaJudgment": ("cortex.memory.metamemory", "MetaJudgment"),
    "MetamemoryIndex": ("cortex.memory.metamemory", "MetamemoryIndex"),
    "MetamemoryMonitor": ("cortex.memory.metamemory", "MetamemoryMonitor"),
    "MetamemoryStats": ("cortex.memory.metamemory", "MetamemoryStats"),
    "RetrievalOutcome": ("cortex.memory.metamemory", "RetrievalOutcome"),
    "Verdict": ("cortex.memory.metamemory", "Verdict"),
    "build_memory_card": ("cortex.memory.metamemory", "build_memory_card"),
    # models
    "EpisodicSnapshot": ("cortex.memory.models", "EpisodicSnapshot"),
    "MemoryEntry": ("cortex.memory.models", "MemoryEntry"),
    "MemoryEvent": ("cortex.memory.models", "MemoryEvent"),
    # navigator
    "ClusterInfo": ("cortex.memory.navigator", "ClusterInfo"),
    "KnowledgeMap": ("cortex.memory.navigator", "KnowledgeMap"),
    "NavigationState": ("cortex.memory.navigator", "NavigationState"),
    "SemanticNavigator": ("cortex.memory.navigator", "SemanticNavigator"),
    "SemanticPath": ("cortex.memory.navigator", "SemanticPath"),
    # pipeline
    "NeuromorphicPipeline": ("cortex.memory.pipeline", "NeuromorphicPipeline"),
    "QueryResult": ("cortex.memory.pipeline", "QueryResult"),
    "StoreResult": ("cortex.memory.pipeline", "StoreResult"),
    # resonance
    "AdaptiveResonanceGate": ("cortex.memory.resonance", "AdaptiveResonanceGate"),
    # sleep
    "SleepCycleReport": ("cortex.memory.sleep", "SleepCycleReport"),
    "SleepOrchestrator": ("cortex.memory.sleep", "SleepOrchestrator"),
    # sparse
    "MushroomBodyEncoder": ("cortex.memory.sparse", "MushroomBodyEncoder"),
    # temporal_health
    "HealthReport": ("cortex.memory.temporal_health", "HealthReport"),
    "SchedulerConfig": ("cortex.memory.temporal_health", "SchedulerConfig"),
    "TemporalHealthScheduler": ("cortex.memory.temporal_health", "TemporalHealthScheduler"),
    # void_detector
    "EpistemicAnalysis": ("cortex.memory.void_detector", "EpistemicAnalysis"),
    "EpistemicState": ("cortex.memory.void_detector", "EpistemicState"),
    "EpistemicVoidDetector": ("cortex.memory.void_detector", "EpistemicVoidDetector"),
    # working
    "WorkingMemoryL1": ("cortex.memory.working", "WorkingMemoryL1"),
}


def __getattr__(name: str) -> object:
    """Lazy-load memory symbols on first access (PEP 562)."""
    if name == "VectorStoreL2":
        # Special case: VectorStoreL2 has a fallback chain
        try:
            from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

            val = SovereignVectorStoreL2
        except ImportError:
            # cortex.memory.vector_store was removed; no further fallback
            val = None  # type: ignore[assignment]
        globals()["VectorStoreL2"] = val
        return val

    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.memory' has no attribute {name!r}")
