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
            try:
                from cortex.memory.vector_store import (
                    VectorStoreL2 as _VL2,  # type: ignore[import-not-found]
                )

                val = _VL2
            except ImportError:
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
