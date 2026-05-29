"""Evolution Operations Mixin — genetic operators and adversarial processes."""
import asyncio
import logging
import random
import secrets
import sqlite3
from typing import TYPE_CHECKING
from cortex.extensions.evolution.action import SymbolicActionState
from cortex.extensions.evolution.agents import AgentDomain, Mutation, MutationType, SovereignAgent, SubAgent
from cortex.extensions.evolution.cortex_metrics import DomainMetrics
from cortex.extensions.evolution.models import EvolutionMetric, EvolutionMutation
from cortex.extensions.evolution.strategies import DEFAULT_STRATEGIES
if TYPE_CHECKING:
    from cortex.extensions.evolution.action import SymbolicActionEngine
    from cortex.extensions.evolution.ledger_db import EvolutionLedgerDB
    from cortex.extensions.evolution.models import EngineParameters
    from cortex.extensions.gate.ouroboros import OuroborosGate
    from cortex.extensions.sovereign.endocrine import DigitalEndocrine
    from cortex.ledger import SovereignLedger
logger = logging.getLogger('cortex.extensions.evolution.engine.ops')

class EvolutionOpsMixin:
    """Mixin for genetic operations, extinctions, and adversarial grounding."""
    if TYPE_CHECKING:
        params: EngineParameters
        sovereigns: list[SovereignAgent]
        cycle_count: int
        _endocrine: DigitalEndocrine
        _ledger: SovereignLedger
        _evolution_ledger: EvolutionLedgerDB
        _ouroboros: OuroborosGate | None
        _action_engine: SymbolicActionEngine
        _broadcast_task: asyncio.Task | None
