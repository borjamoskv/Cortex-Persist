"""CORTEX Pipeline - Stage implementations.

Reality Level: C5-REAL
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from cortex.pipeline import ContextPacket, PipelineRequest
from cortex.pipeline._orchestrator_exceptions import BudgetExhaustedError

logger = logging.getLogger("cortex.pipeline.orchestrator")


class StagesMixin:
    """Implementations for all 6 pipeline stages."""

    def _ingress(self, request: PipelineRequest) -> None:
        """Validate incoming request."""
        if not request.intent or not request.intent.strip():
            raise ValueError("Empty intent - nothing to execute")

        if request.budget_limit_usd <= 0:
            raise ValueError("Budget must be positive")

        if request.timeout_s <= 0:
            raise ValueError("Timeout must be positive")

        logger.debug(
            "  [INGRESS] Validated: budget=$%.2f timeout=%.0fs tenant=%s",
            request.budget_limit_usd,
            request.timeout_s,
            request.tenant_id,
        )

    def _assemble_context(self, request: PipelineRequest) -> ContextPacket:
        """Gather relevant context from all knowledge sources."""
        if self._context is None:
            logger.debug("  [CONTEXT] No assembler configured - empty context")
            return ContextPacket()

        return self._context.assemble(
            intent=request.intent,
            hints=request.context_hints,
            tenant_id=request.tenant_id,
        )

    def _plan(self, request: PipelineRequest, context: ContextPacket) -> dict[str, Any]:
        """Route request to appropriate agent(s)."""
        if self._router is None:
            return {
                "agents": ["general"],
                "strategy": "sequential",
                "max_tokens": 4096,
            }

        return self._router.route(
            intent=request.intent,
            context=context,
            budget_remaining=request.budget_limit_usd,
        )

    def _execute(
        self,
        request: PipelineRequest,
        context: ContextPacket,
        plan: dict[str, Any],
    ) -> Any:
        """Execute the planned agent chain."""
        if self._budget:
            budget_state = self._budget.get_mission_budget(request.mission_id)
            if budget_state and budget_state.total_cost_usd >= request.budget_limit_usd:
                raise BudgetExhaustedError(
                    f"Mission {request.mission_id} already at "
                    f"${budget_state.total_cost_usd:.4f} "
                    f"(limit: ${request.budget_limit_usd:.4f})"
                )

        if self._executor is not None:
            import asyncio

            coro_factory = lambda: self._executor.execute(  # noqa: E731
                intent=request.intent,
                context=context,
                plan=plan,
                budget_remaining=request.budget_limit_usd,
            )

            try:
                asyncio.get_running_loop()
                return coro_factory()
            except RuntimeError:
                return asyncio.run(coro_factory())

        agents = plan.get("agents", ["general"])
        results = []

        for agent_id in agents:
            logger.debug("  [EXECUTION] Running agent: %s", agent_id)
            agent_result = {
                "agent_id": agent_id,
                "status": "executed",
                "content": None,
            }
            results.append(agent_result)

        if len(results) == 1:
            return results[0]
        return {"multi_agent": True, "results": results}

    def _persist(self, request: PipelineRequest, output: Any) -> str:
        """Hash-chain the result into the audit ledger."""
        output_bytes = json.dumps(output, sort_keys=True, default=str).encode()
        result_hash = hashlib.sha256(output_bytes).hexdigest()

        if self.engine is not None:
            try:
                import asyncio
                from cortex.utils.time_utils import get_utc_timestamp

                async def persist_to_engine():
                    async with self.engine.session() as conn:
                        await conn.execute(
                            "INSERT INTO execution_log (mission_id, result_hash, tenant_id, completed_at, status) VALUES (?, ?, ?, ?, ?)",
                            (
                                request.mission_id,
                                result_hash,
                                request.tenant_id,
                                get_utc_timestamp(),
                                "SUCCESS",
                            ),
                        )
                        await conn.commit()

                try:
                    asyncio.get_running_loop()
                    asyncio.create_task(persist_to_engine())
                except RuntimeError:
                    asyncio.run(persist_to_engine())
            except Exception as e:
                logger.warning("  [PERSIST] Engine SQLite write failed: %s", e)

        elif self._ledger:
            try:
                self._ledger.append(
                    mission_id=request.mission_id,
                    result_hash=result_hash,
                    tenant_id=request.tenant_id,
                )
            except Exception as e:
                logger.warning("  [PERSIST] Ledger write failed: %s", e)

        logger.debug("  [PERSIST] Hash: %s", result_hash[:16])
        return result_hash

    def _deliver(self, request: PipelineRequest, output: Any) -> None:
        """Deliver result to the specified target."""
        if self._delivery is None:
            logger.info("  [EGRESS] No delivery manager - result logged only")
            return

        self._delivery.deliver(
            output=output,
            target=request.delivery,
            mission_id=request.mission_id,
        )
