"""
CORTEX v8.0 — Swarm Architecture.

Integrates KETER-∞ multi-agent swarm orchestration,
the Code Smith (Safe Self-Evolution), the Conflict Resolution Protocol,
the Josu Proactive Daemon, and the NightShift Pipeline.
"""

from cortex.extensions.swarm.code_smith import ASTValidator, CodeSmith
from cortex.extensions.swarm.conflict_resolution import ConflictResolver, ConflictType
from cortex.extensions.swarm.infinite_minds import AgentMind, InfiniteMindsManager
from cortex.extensions.swarm.josu_daemon import JosuProactiveDaemon
from cortex.extensions.swarm.nightshift_pipeline import NightShiftPipeline

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
