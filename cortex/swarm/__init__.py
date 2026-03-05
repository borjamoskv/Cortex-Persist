"""
CORTEX v8.0 — Swarm Architecture.

Integrates KETER-∞ multi-agent swarm orchestration,
the Code Smith (Safe Self-Evolution), and the Conflict Resolution Protocol.
"""

from cortex.swarm.code_smith import ASTValidator, CodeSmith
from cortex.swarm.conflict_resolution import ConflictResolver, ConflictType
from cortex.swarm.infinite_minds import AgentMind, InfiniteMindsManager

__all__ = [
    "AgentMind",
    "ASTValidator",
    "CodeSmith",
    "ConflictResolver",
    "ConflictType",
    "InfiniteMindsManager",
]
