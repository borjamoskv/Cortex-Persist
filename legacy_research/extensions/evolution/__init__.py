# [C5-REAL] Exergy-Maximized
# cortex/evolution/__init__.py
"""Continuous Evolution Engine for CORTEX Sovereign Swarm.

10 agents × 10 subagents = 100 entities improving forever.
"""

from legacy_research.extensions.evolution.agents import (
    AgentDomain,
    Mutation,
    MutationType,
    SovereignAgent,
    SubAgent,
    create_sovereign_swarm,
)
from legacy_research.extensions.evolution.engine import EvolutionEngine
from legacy_research.extensions.evolution.ledger_db import EvolutionLedgerDB
from legacy_research.extensions.evolution.models import (
    EvolutionMetric,
    EvolutionMutation,
    EvolutionType,
)
from legacy_research.extensions.evolution.persistence import load_swarm, save_swarm

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
