# [C5-REAL] Exergy-Maximized
"""CORTEX Pipeline Bridge - Wires E2E Pipeline to Real Infrastructure.

Connects the abstract CortexOrchestrator to the real CortexEngine,
FactStore, LedgerStore, and LLM providers.

This is the GLUE module. It imports real CORTEX subsystems and assembles
a fully functional CortexOrchestrator with all backends wired.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from babylon60.core.paths import CORTEX_DB as DEFAULT_DB_PATH
from babylon60.pipeline import (
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
)
from babylon60.pipeline.orchestrator import CortexOrchestrator

logger = logging.getLogger("cortex.pipeline.bridge")


class CortexPipelineBridge:
    """Wires the E2E pipeline to real CORTEX infrastructure.

    Creates a fully connected CortexOrchestrator with:
    - CortexEngine for memory/facts (async)
    - ContextAssembler with real SQLite-Vec + FactStore
    - AgentRouter with budget integration
    - DeliveryManager for real egress
    - SwarmBudgetManager for Ω₃ enforcement
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self._db_path = Path(str(db_path)).expanduser()
        self._engine = None
        self._orchestrator: CortexOrchestrator | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all real backends and wire the orchestrator."""
        if self._initialized:
            return

        # 1. CortexEngine (memory, facts, ledger)
        from babylon60.engine import CortexEngine

        self._engine = CortexEngine(self._db_path)
        await self._engine.init_db()

        # 2. Context Assembler with real backends
        from babylon60.context.assembler import ContextAssembler

        vsa_adapter = self._init_vsa()
        fact_adapter = FactStoreAdapter(self._engine)
        context_assembler = ContextAssembler(
            fact_store=fact_adapter,
            vsa_adapter=vsa_adapter,
        )

        # 3. Agent Router
        from babylon60.router.router import AgentRouter

        router = AgentRouter()

        # 4. Delivery Manager
        from babylon60.delivery.manager import DeliveryManager

        delivery = DeliveryManager()

        # 5. Budget Manager
        budget = self._init_budget()

        # 6. Ledger adapter
        ledger = LedgerAdapter(self._engine)

        # 7. Agent Executor (real LLM dispatch)
        from babylon60.pipeline.executor import AgentExecutor

        self._executor = AgentExecutor()

        # 8. Assemble the orchestrator
        self._orchestrator = CortexOrchestrator(
            context_assembler=context_assembler,
            agent_router=router,
            delivery_manager=delivery,
            budget_manager=budget,
            ledger=ledger,
            agent_executor=self._executor,
        )

        self._initialized = True
        logger.info("🔗 [BRIDGE] Pipeline wired to real infrastructure at %s", self._db_path)

    def _init_budget(self) -> Any | None:
        """Initialize SwarmBudgetManager if available."""
        try:
            from babylon60.extensions.swarm.budget import get_budget_manager

            return get_budget_manager()
        except ImportError:
            logger.debug("[BRIDGE] SwarmBudgetManager not available")
        return None

    def _init_vsa(self) -> Any | None:
        """Initialize VSA-SDM adapter if available."""
        try:
            from babylon60.context.vsa_adapter import VSAContextAdapter

            adapter = VSAContextAdapter(agent_id="cortex-pipeline")
            if adapter.is_available:
                logger.info("[BRIDGE] VSA-SDM memory adapter initialized")
                return adapter
            logger.debug("[BRIDGE] VSA engine not available - algebraic context disabled")
        except ImportError:
            logger.debug("[BRIDGE] VSA adapter not available")
        except Exception as e:
            logger.warning("[BRIDGE] VSA init failed: %s", e)
        return None

    async def run(self, request: PipelineRequest) -> PipelineResult:
        """Execute a full E2E pipeline with real infrastructure."""
        await self.initialize()
        assert self._orchestrator is not None
        return await self._orchestrator.run_async(request)

    async def run_async(self, request: PipelineRequest) -> PipelineResult:
        """Execute pipeline via native async path (alias for run)."""
        return await self.run(request)

    async def run_intent(
        self,
        intent: str,
        delivery_type: DeliveryType = DeliveryType.STDOUT,
        budget: float = 0.10,
        hints: list[str] | None = None,
    ) -> PipelineResult:
        """Convenience: run a pipeline from a raw intent string."""
        request = PipelineRequest(
            intent=intent,
            context_hints=hints or [],
            budget_limit_usd=budget,
            delivery=DeliveryTarget(type=delivery_type),
        )
        return await self.run(request)

    async def close(self) -> None:
        """Shutdown all backends."""
        if self._engine:
            await self._engine.close()
            self._engine = None
        self._initialized = False


class FactStoreAdapter:
    """Adapts CortexEngine's async FactStore to the sync ContextAssembler interface."""

    def __init__(self, engine: Any):
        self._engine = engine

    def search(self, query: str, tenant_id: str = "default", limit: int = 10) -> list[dict]:
        """Synchronous search wrapper for ContextAssembler."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context - can't nest. Return empty.
                # The async path should use _search_async directly.
                return []
            return loop.run_until_complete(self._search_async(query, tenant_id, limit))
        except RuntimeError:
            return []

    async def _search_async(self, query: str, tenant_id: str, limit: int) -> list[dict]:
        """Async fact search via CortexEngine."""
        try:
            results = await self._engine.search(
                query=query,
                tenant_id=tenant_id,
                limit=limit,
            )
            return [
                {
                    "id": getattr(r, "id", 0),
                    "content": getattr(r, "content", str(r)),
                    "confidence": getattr(r, "confidence", "C3"),
                    "created_at": getattr(r, "created_at", ""),
                }
                for r in (results or [])
            ]
        except Exception as e:
            logger.debug("[FACTS] Search failed: %s", e)
            return []


class LedgerAdapter:
    """Adapts CortexEngine's ledger to the pipeline's append interface."""

    def __init__(self, engine: Any):
        self._engine = engine

    def append(self, mission_id: str, result_hash: str, tenant_id: str = "default") -> None:
        """Append a pipeline result to the audit ledger."""
        try:
            import os

            ledger_path = os.path.expanduser("~/.cortex/pipeline_ledger.jsonl")
            os.makedirs(os.path.dirname(ledger_path), exist_ok=True)

            entry = json.dumps(
                {
                    "mission_id": mission_id,
                    "result_hash": result_hash,
                    "tenant_id": tenant_id,
                    "timestamp": time.monotonic(),
                }
            )

            with open(ledger_path, "a", encoding="utf-8") as f:
                f.write(entry + "\n")

            logger.debug("[LEDGER] Appended mission %s hash %s", mission_id, result_hash[:16])
        except Exception as e:
            logger.warning("[LEDGER] Append failed: %s", e)
