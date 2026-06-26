# [C5-REAL] Exergy-Maximized
# cortex/evolution/__init__.py
"""Continuous Evolution Engine for CORTEX Sovereign Swarm.

10 agents × 10 subagents = 100 entities improving forever.
"""

from cortex_extensions.evolution.agents import (
    AgentDomain,
    Mutation,
    MutationType,
    SovereignAgent,
    SubAgent,
    create_sovereign_swarm,
)
from cortex_extensions.evolution.engine import EvolutionEngine
from cortex_extensions.evolution.ledger_db import EvolutionLedgerDB
from cortex_extensions.evolution.models import (
    EvolutionMetric,
    EvolutionMutation,
    EvolutionType,
)
from cortex_extensions.evolution.persistence import load_swarm, save_swarm

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
