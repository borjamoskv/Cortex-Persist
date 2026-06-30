# [C5-REAL] Exergy-Maximized
# cortex/evolution/__init__.py
"""Continuous Evolution Engine for CORTEX Sovereign Swarm.

10 agents × 10 subagents = 100 entities improving forever.
"""

from babylon60.extensions.evolution.agents import (
    AgentDomain,
    EnneagramSovereign,
    EnneagramSubAgent,
    Mutation,
    MutationType,
    create_sovereign_swarm,
)
from babylon60.extensions.evolution.engine import EvolutionEngine
from babylon60.extensions.evolution.ledger_db import EvolutionLedgerDB
from babylon60.extensions.evolution.models import (
    EvolutionMetric,
    EvolutionMutation,
    EvolutionType,
)
from babylon60.extensions.evolution.persistence import load_swarm, save_swarm

__all__ = [
    "AgentDomain",
    "EvolutionEngine",
    "EvolutionLedgerDB",
    "EvolutionMetric",
    "EvolutionMutation",
    "EvolutionType",
    "Mutation",
    "MutationType",
    "EnneagramSovereign",
    "EnneagramSubAgent",
    "create_sovereign_swarm",
    "load_swarm",
    "save_swarm",
]
