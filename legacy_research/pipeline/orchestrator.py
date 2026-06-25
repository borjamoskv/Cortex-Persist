# [C5-REAL] Exergy-Maximized
"""CORTEX Pipeline - Sovereign E2E Orchestrator.

Wires Ingress → Context → Plan → Execute → Persist → Egress
into a single deterministic flow with full telemetry.

Reality Level: C5-REAL
"""

from __future__ import annotations

from typing import Any

from legacy_research.pipeline._orchestrator_runner import RunnerMixin
from legacy_research.pipeline._orchestrator_stages import StagesMixin


class CortexOrchestrator(StagesMixin, RunnerMixin):
    """The central E2E orchestrator for CORTEX.

    Executes a 6-stage pipeline:
    1. INGRESS  - Validate and parse the request
    2. CONTEXT  - Assemble relevant knowledge
    3. PLANNING - Route to agent(s)
    4. EXECUTION - Run agent(s) with budget tracking
    5. PERSISTENCE - Hash-chain result to ledger
    6. EGRESS   - Deliver result to target
    """

    def __init__(
        self,
        context_assembler: Any | None = None,
        agent_router: Any | None = None,
        delivery_manager: Any | None = None,
        budget_manager: Any | None = None,
        ledger: Any | None = None,
        agent_executor: Any | None = None,
        engine: Any | None = None,
    ):
        self._context = context_assembler
        self._router = agent_router
        self._delivery = delivery_manager
        self._budget = budget_manager
        self._ledger = ledger
        self._executor = agent_executor
        self.engine = engine
        self._traces = []
        self._cancel_event = None
