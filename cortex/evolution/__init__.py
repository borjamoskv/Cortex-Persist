# cortex/evolution/__init__.py
"""Continuous Evolution Engine for CORTEX Sovereign Swarm.

10 agents × 10 subagents = 100 entities improving forever.
"""

from cortex.evolution.agents import (
    AgentDomain,
    Mutation,
    MutationType,
    SovereignAgent,
    SubAgent,
    create_sovereign_swarm,
)
from cortex.evolution.engine import EvolutionEngine
from cortex.evolution.ledger_db import EvolutionLedgerDB
from cortex.evolution.models import (
    EvolutionMetric,
    EvolutionMutation,
    EvolutionType,
)
from cortex.evolution.persistence import load_swarm, save_swarm

__all__ = [
    "AgentDomain",
    "EvolutionEngine",
    "EvolutionLedgerDB",
    "EvolutionMetric",
    "EvolutionMutation",
    "EvolutionType",
    "Mutation",
    "MutationType",
    "SovereignAgent",
    "SubAgent",
    "create_sovereign_swarm",
    "load_swarm",
    "save_swarm",
]
