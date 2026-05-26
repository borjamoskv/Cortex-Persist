"""CORTEX Pipeline — Sovereign E2E Orchestrator.

Wires Ingress → Context → Plan → Execute → Persist → Egress
into a single deterministic flow with full telemetry.

Law Ω₁: Stochastic output → Deterministic boundary (Guard) → Close.
Law Ω₃: Budget enforcement at every stage transition.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from cortex.pipeline import (
    ContextPacket,
    DeliveryTarget,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)

logger = logging.getLogger("cortex.pipeline.orchestrator")


class CortexOrchestrator:
    """The central E2E orchestrator for CORTEX.

    Executes a 6-stage pipeline:
    1. INGRESS  — Validate and parse the request
    2. CONTEXT  — Assemble relevant knowledge
    3. PLANNING — Route to agent(s)
    4. EXECUTION — Run agent(s) with budget tracking
    5. PERSISTENCE — Hash-chain result to ledger
    6. EGRESS   — Deliver result to target
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
        self._traces: list[StageTrace] = []
        self._cancel_event: Any | None = None

    async def run_async(self, request: PipelineRequest) -> PipelineResult:
        """Execute the full E2E pipeline asynchronously.

        Native async implementation with proper timeout/cancellation.
        Each stage runs via asyncio — no ThreadPoolExecutor deadlocks.

        Returns a PipelineResult with full provenance and telemetry.
        """
        import asyncio

        try:
            return await asyncio.wait_for(
                self._run_async_impl(request),
                timeout=request.timeout_s,
            )
        except asyncio.TimeoutError:
            return PipelineResult(
                mission_id=request.mission_id,
                status=PipelineStatus.FAILED,
                error=f"Pipeline timeout after {request.timeout_s}s",
                completed_at=time.time(),
            )
        except asyncio.CancelledError:
            return PipelineResult(
                mission_id=request.mission_id,
                status=PipelineStatus.CANCELLED,
                error="Pipeline cancelled",
                completed_at=time.time(),
            )

    async def _run_async_impl(self, request: PipelineRequest) -> PipelineResult:
        """Native async pipeline implementation."""
        import asyncio

        logger.info(
            "🚀 [E2E-ASYNC] Pipeline START mission=%s intent='%s'",
            request.mission_id,
            request.intent[:80],
        )

        result = PipelineResult(
            mission_id=request.mission_id,
            status=PipelineStatus.RUNNING,
        )
        self._traces = []

        try:
            # ── Stage 1: INGRESS ──
            await self._run_stage_async(
                PipelineStage.INGRESS,
                lambda: self._ingress(request),
            )

            # ── Stage 2: CONTEXT ──
            context_packet = await self._run_stage_async(
                PipelineStage.CONTEXT,
                lambda: self._assemble_context(request),
            )

            # ── Stage 3: PLANNING ──
            execution_plan = await self._run_stage_async(
                PipelineStage.PLANNING,
                lambda: self._plan(request, context_packet),
            )

            # ── Stage 4: EXECUTION ──
            output = await self._run_stage_async(
                PipelineStage.EXECUTION,
                lambda: self._execute(request, context_packet, execution_plan),
                is_async_executor=True,
            )

            # ── Stage 5: PERSISTENCE ──
            ledger_hash = await self._run_stage_async(
                PipelineStage.PERSISTENCE,
                lambda: self._persist(request, output),
            )

            # ── Stage 6: EGRESS ──
            await self._run_stage_async(
                PipelineStage.EGRESS,
                lambda: self._deliver(request, output),
            )

            # ── Assemble final result ──
            result.status = PipelineStatus.SUCCESS
            result.output = output
            result.ledger_hash = ledger_hash or ""
            result.context_used = [
                ki.get("source", "unknown")
                for ki in (context_packet.knowledge_items if context_packet else [])
            ]
            result.agent_chain = execution_plan.get("agents", []) if execution_plan else []
            result.cost_usd = sum(t.cost_usd for t in self._traces)
            result.stages = list(self._traces)
            result.completed_at = time.time()

        except BudgetExhaustedError as e:
            result.status = PipelineStatus.BUDGET_EXHAUSTED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.time()

        except PipelineCancelledError as e:
            result.status = PipelineStatus.CANCELLED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.time()

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.time()
            logger.error(
                "❌ [E2E-ASYNC] Pipeline FAILED mission=%s: %s",
                request.mission_id,
                e,
            )

        logger.info(
            "✅ [E2E-ASYNC] Pipeline %s mission=%s latency=%.0fms",
            result.status.value,
            result.mission_id,
            result.latency_ms,
        )
        return result

    async def _run_stage_async(
        self,
        stage: PipelineStage,
        fn: Any,
        is_async_executor: bool = False,
    ) -> Any:
        """Execute a pipeline stage asynchronously with timing."""
        import asyncio

        start = time.time()
        error_msg = None
        result = None

        try:
            if is_async_executor and self._executor is not None:
                result = fn()
                if asyncio.iscoroutine(result):
                    result = await result
            else:
                result = await asyncio.to_thread(fn)
        except (BudgetExhaustedError, PipelineCancelledError):
            raise
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            end = time.time()
            trace = StageTrace(
                stage=stage,
                started_at=start,
                ended_at=end,
                error=error_msg,
            )
            self._traces.append(trace)

        return result

    async def run_streaming(self, request: PipelineRequest):
        """Execute pipeline yielding StageTrace events per stage.

        Final yield is the PipelineResult.
        """
        self._traces = []
        result = PipelineResult(
            mission_id=request.mission_id,
            status=PipelineStatus.RUNNING,
        )

        context_packet = None
        execution_plan = None
        output = None
        ledger_hash = None

        try:
            await self._run_stage_async(PipelineStage.INGRESS, lambda: self._ingress(request))
            yield self._traces[-1]

            context_packet = await self._run_stage_async(
                PipelineStage.CONTEXT, lambda: self._assemble_context(request)
            )
            yield self._traces[-1]

            execution_plan = await self._run_stage_async(
                PipelineStage.PLANNING,
                lambda: self._plan(request, context_packet),
            )
            yield self._traces[-1]

            output = await self._run_stage_async(
                PipelineStage.EXECUTION,
                lambda: self._execute(request, context_packet, execution_plan),
                is_async_executor=True,
            )
            yield self._traces[-1]

            ledger_hash = await self._run_stage_async(
                PipelineStage.PERSISTENCE, lambda: self._persist(request, output)
            )
            yield self._traces[-1]

            await self._run_stage_async(
                PipelineStage.EGRESS, lambda: self._deliver(request, output)
            )
            yield self._traces[-1]

            result.status = PipelineStatus.SUCCESS
            result.output = output
            result.ledger_hash = ledger_hash or ""
            result.stages = list(self._traces)
            result.completed_at = time.time()

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.time()

        yield result

    def run(self, request: PipelineRequest) -> PipelineResult:
        """Execute the full E2E pipeline synchronously.

        Returns a PipelineResult with full provenance and telemetry.
        """
        logger.info(
            "🚀 [E2E] Pipeline START mission=%s intent='%s'",
            request.mission_id,
            request.intent[:80],
        )

        result = PipelineResult(
            mission_id=request.mission_id,
            status=PipelineStatus.RUNNING,
        )
        self._traces = []

        try:
            # ── Stage 1: INGRESS ──
            self._run_stage(
                PipelineStage.INGRESS,
                lambda: self._ingress(request),
            )

            # ── Stage 2: CONTEXT ──
            context_packet = self._run_stage(
                PipelineStage.CONTEXT,
                lambda: self._assemble_context(request),
            )

            # ── Stage 3: PLANNING ──
            execution_plan = self._run_stage(
                PipelineStage.PLANNING,
                lambda: self._plan(request, context_packet),
            )

            # ── Stage 4: EXECUTION ──
            output = self._run_stage(
                PipelineStage.EXECUTION,
                lambda: self._execute(request, context_packet, execution_plan),
            )

            # ── Stage 5: PERSISTENCE ──
            ledger_hash = self._run_stage(
                PipelineStage.PERSISTENCE,
                lambda: self._persist(request, output),
            )

            # ── Stage 6: EGRESS ──
            self._run_stage(
                PipelineStage.EGRESS,
                lambda: self._deliver(request, output),
            )

            # ── Assemble final result ──
            result.status = PipelineStatus.SUCCESS
            result.output = output
            result.ledger_hash = ledger_hash or ""
            result.context_used = [
                ki.get("source", "unknown")
                for ki in (context_packet.knowledge_items if context_packet else [])
            ]
            result.agent_chain = execution_plan.get("agents", []) if execution_plan else []
            result.cost_usd = sum(t.cost_usd for t in self._traces)
            result.stages = list(self._traces)
            result.completed_at = time.time()

        except BudgetExhaustedError as e:
            result.status = PipelineStatus.BUDGET_EXHAUSTED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.time()
            logger.critical("🛑 [Ω₃] %s", e)

        except PipelineCancelledError as e:
            result.status = PipelineStatus.CANCELLED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.time()

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.time()
            logger.error("❌ [E2E] Pipeline FAILED mission=%s: %s", request.mission_id, e)

        logger.info(
            "✅ [E2E] Pipeline %s mission=%s latency=%.0fms cost=$%.4f",
            result.status.value,
            result.mission_id,
            result.latency_ms,
            result.cost_usd,
        )
        return result

    # ── Stage Implementations ──

    def _run_stage(self, stage: PipelineStage, fn: Any) -> Any:
        """Execute a stage with timing and error capture."""
        start = time.time()
        error_msg = None
        result = None

        try:
            result = fn()
            import asyncio

            if asyncio.iscoroutine(result):
                try:
                    asyncio.get_running_loop()
                    import threading

                    res_val = None
                    exc_val = None

                    def _worker():
                        nonlocal res_val, exc_val
                        try:
                            res_val = asyncio.run(result)
                        except Exception as ex:
                            exc_val = ex

                    t = threading.Thread(target=_worker)
                    t.start()
                    t.join()
                    if exc_val:
                        raise exc_val
                    result = res_val
                except RuntimeError:
                    result = asyncio.run(result)
        except (BudgetExhaustedError, PipelineCancelledError):
            raise
        except Exception as e:
            error_msg = str(e)
            raise

        finally:
            end = time.time()
            trace = StageTrace(
                stage=stage,
                started_at=start,
                ended_at=end,
                error=error_msg,
            )
            self._traces.append(trace)
            logger.debug(
                "  [%s] %.1fms %s",
                stage.value,
                trace.latency_ms,
                "✓" if not error_msg else f"✗ {error_msg}",
            )

        return result

    def _ingress(self, request: PipelineRequest) -> None:
        """Validate incoming request."""
        if not request.intent or not request.intent.strip():
            raise ValueError("Empty intent — nothing to execute")

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
            logger.debug("  [CONTEXT] No assembler configured — empty context")
            return ContextPacket()

        return self._context.assemble(
            intent=request.intent,
            hints=request.context_hints,
            tenant_id=request.tenant_id,
        )

    def _plan(self, request: PipelineRequest, context: ContextPacket) -> dict[str, Any]:
        """Route request to appropriate agent(s)."""
        if self._router is None:
            # Default: single general-purpose agent
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
        # Budget pre-check via Ω₃
        if self._budget:
            budget_state = self._budget.get_mission_budget(request.mission_id)
            if budget_state and budget_state.total_cost_usd >= request.budget_limit_usd:
                raise BudgetExhaustedError(
                    f"Mission {request.mission_id} already at "
                    f"${budget_state.total_cost_usd:.4f} "
                    f"(limit: ${request.budget_limit_usd:.4f})"
                )

        # Real LLM dispatch via AgentExecutor
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
                # Already inside an async context — return the coroutine directly
                # so the caller can await it natively within the running event loop.
                return coro_factory()
            except RuntimeError:
                # No running loop — safe to use asyncio.run() directly.
                return asyncio.run(coro_factory())

        # Fallback: structured stub when no executor is available
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
        # Compute deterministic hash of the output
        output_bytes = json.dumps(output, sort_keys=True, default=str).encode()
        result_hash = hashlib.sha256(output_bytes).hexdigest()

        # If we have a sovereign SQLite engine, persist execution log
        if self.engine is not None:
            try:
                import asyncio
                import aiosqlite
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

                # We are in a to_thread worker from _run_stage_async
                # so we can use asyncio.run to execute the DB write safely if no loop is here
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
            # Fallback: log output
            logger.info("  [EGRESS] No delivery manager — result logged only")
            return

        self._delivery.deliver(
            output=output,
            target=request.delivery,
            mission_id=request.mission_id,
        )


class BudgetExhaustedError(RuntimeError):
    """Raised when a mission exceeds its Ω₃ exergy ceiling."""


class PipelineCancelledError(RuntimeError):
    """Raised when a pipeline run is cancelled externally."""
