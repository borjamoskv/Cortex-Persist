"""
CORTEX v8.0 — Swarm Architecture.

Integrates KETER-∞ multi-agent swarm orchestration,
the Code Smith (Safe Self-Evolution), the Conflict Resolution Protocol,
the Josu Proactive Daemon, and the NightShift Pipeline.
"""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    """Lazy import for swarm components to avoid heavy dependencies (like numpy)."""
    if name == "CodeSmith":
        from cortex.extensions.swarm.code_smith import CodeSmith
        return CodeSmith
    if name == "ASTValidator":
        from cortex.extensions.swarm.code_smith import ASTValidator
        return ASTValidator
    if name == "ConflictResolver":
        from cortex.extensions.swarm.conflict_resolution import ConflictResolver
        return ConflictResolver
    if name == "ConflictType":
        from cortex.extensions.swarm.conflict_resolution import ConflictType
        return ConflictType
    if name == "AgentMind":
        from cortex.extensions.swarm.infinite_minds import AgentMind
        return AgentMind
    if name == "InfiniteMindsManager":
        from cortex.extensions.swarm.infinite_minds import InfiniteMindsManager
        return InfiniteMindsManager
    if name == "JosuProactiveDaemon":
        from cortex.extensions.swarm.josu_daemon import JosuProactiveDaemon
        return JosuProactiveDaemon
    if name == "NightShiftPipeline":
        from cortex.extensions.swarm.nightshift_pipeline import NightShiftPipeline
        return NightShiftPipeline

    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "AgentMind",
    "ASTValidator",
    "CodeSmith",
    "ConflictResolver",
    "ConflictType",
    "InfiniteMindsManager",
    "JosuProactiveDaemon",
    "NightShiftPipeline",
]
