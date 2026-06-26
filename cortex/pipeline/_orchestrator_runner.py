# [C5-REAL] Exergy-Maximized
"""CORTEX Pipeline - Runner implementations.

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from cortex.pipeline import (
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)
from cortex.pipeline._orchestrator_exceptions import (
    BudgetExhaustedError,
    PipelineCancelledError,
)

logger = logging.getLogger("cortex.pipeline.orchestrator")


class RunnerMixin:
    """Synchronous and asynchronous execution loops for CortexOrchestrator."""

    async def run_async(self, request: PipelineRequest) -> PipelineResult:
        """Execute the full E2E pipeline asynchronously."""
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
                completed_at=time.monotonic(),
            )
        except asyncio.CancelledError:
            return PipelineResult(
                mission_id=request.mission_id,
                status=PipelineStatus.CANCELLED,
                error="Pipeline cancelled",
                completed_at=time.monotonic(),
            )

    async def _run_async_impl(self, request: PipelineRequest) -> PipelineResult:
        """Native async pipeline implementation."""
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
                lambda: self._ingress(request),  # pyright: ignore[reportAttributeAccessIssue]
            )

            # ── Stage 2: CONTEXT ──
            context_packet = await self._run_stage_async(
                PipelineStage.CONTEXT,
                lambda: self._assemble_context(request),  # pyright: ignore[reportAttributeAccessIssue]
            )

            # ── Stage 3: PLANNING ──
            execution_plan = await self._run_stage_async(
                PipelineStage.PLANNING,
                lambda: self._plan(request, context_packet),  # pyright: ignore[reportAttributeAccessIssue]
            )

            # ── Stage 4: EXECUTION ──
            output = await self._run_stage_async(
                PipelineStage.EXECUTION,
                lambda: self._execute(request, context_packet, execution_plan),  # pyright: ignore[reportAttributeAccessIssue]
                is_async_executor=True,
            )

            # ── Stage 5: PERSISTENCE ──
            ledger_hash = await self._run_stage_async(
                PipelineStage.PERSISTENCE,
                lambda: self._persist(request, output),  # pyright: ignore[reportAttributeAccessIssue]
            )

            # ── Stage 6: EGRESS ──
            await self._run_stage_async(
                PipelineStage.EGRESS,
                lambda: self._deliver(request, output),  # pyright: ignore[reportAttributeAccessIssue]
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
            result.completed_at = time.monotonic()

        except BudgetExhaustedError as e:
            result.status = PipelineStatus.BUDGET_EXHAUSTED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.monotonic()

        except PipelineCancelledError as e:
            result.status = PipelineStatus.CANCELLED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.monotonic()

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.monotonic()
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
        start = time.monotonic()
        error_msg = None
        result = None

        try:
            if is_async_executor and self._executor is not None:  # pyright: ignore[reportAttributeAccessIssue]
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
            end = time.monotonic()
            trace = StageTrace(
                stage=stage,
                started_at=start,
                ended_at=end,
                error=error_msg,
            )
            self._traces.append(trace)

        return result

    async def run_streaming(self, request: PipelineRequest):
        """Execute pipeline yielding StageTrace events per stage."""
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
            await self._run_stage_async(PipelineStage.INGRESS, lambda: self._ingress(request))  # pyright: ignore[reportAttributeAccessIssue]
            yield self._traces[-1]

            context_packet = await self._run_stage_async(
                PipelineStage.CONTEXT,
                lambda: self._assemble_context(request),  # pyright: ignore[reportAttributeAccessIssue]
            )
            yield self._traces[-1]

            execution_plan = await self._run_stage_async(
                PipelineStage.PLANNING,
                lambda: self._plan(request, context_packet),  # pyright: ignore[reportAttributeAccessIssue]
            )
            yield self._traces[-1]

            output = await self._run_stage_async(
                PipelineStage.EXECUTION,
                lambda: self._execute(request, context_packet, execution_plan),  # pyright: ignore[reportAttributeAccessIssue]
                is_async_executor=True,
            )
            yield self._traces[-1]

            ledger_hash = await self._run_stage_async(
                PipelineStage.PERSISTENCE,
                lambda: self._persist(request, output),  # pyright: ignore[reportAttributeAccessIssue]
            )
            yield self._traces[-1]

            await self._run_stage_async(
                PipelineStage.EGRESS,
                lambda: self._deliver(request, output),  # pyright: ignore[reportAttributeAccessIssue]
            )
            yield self._traces[-1]

            result.status = PipelineStatus.SUCCESS
            result.output = output
            result.ledger_hash = ledger_hash or ""
            result.stages = list(self._traces)
            result.completed_at = time.monotonic()

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.monotonic()

        yield result

    def run(self, request: PipelineRequest) -> PipelineResult:
        """Execute the full E2E pipeline synchronously."""
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
            self._run_stage(
                PipelineStage.INGRESS,
                lambda: self._ingress(request),  # pyright: ignore[reportAttributeAccessIssue]
            )

            context_packet = self._run_stage(
                PipelineStage.CONTEXT,
                lambda: self._assemble_context(request),  # pyright: ignore[reportAttributeAccessIssue]
            )

            execution_plan = self._run_stage(
                PipelineStage.PLANNING,
                lambda: self._plan(request, context_packet),  # pyright: ignore[reportAttributeAccessIssue]
            )

            output = self._run_stage(
                PipelineStage.EXECUTION,
                lambda: self._execute(request, context_packet, execution_plan),  # pyright: ignore[reportAttributeAccessIssue]
            )

            ledger_hash = self._run_stage(
                PipelineStage.PERSISTENCE,
                lambda: self._persist(request, output),  # pyright: ignore[reportAttributeAccessIssue]
            )

            self._run_stage(
                PipelineStage.EGRESS,
                lambda: self._deliver(request, output),  # pyright: ignore[reportAttributeAccessIssue]
            )

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
            result.completed_at = time.monotonic()

        except BudgetExhaustedError as e:
            result.status = PipelineStatus.BUDGET_EXHAUSTED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.monotonic()
            logger.critical("🛑 [Ω₃] %s", e)

        except PipelineCancelledError as e:
            result.status = PipelineStatus.CANCELLED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.monotonic()

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            result.stages = list(self._traces)
            result.completed_at = time.monotonic()
            logger.error("❌ [E2E] Pipeline FAILED mission=%s: %s", request.mission_id, e)

        logger.info(
            "✅ [E2E] Pipeline %s mission=%s latency=%.0fms cost=$%.4f",
            result.status.value,
            result.mission_id,
            result.latency_ms,
            result.cost_usd,
        )
        return result

    def _run_stage(self, stage: PipelineStage, fn: Any) -> Any:
        """Execute a stage with timing and error capture."""
        start = time.monotonic()
        error_msg = None
        result = None

        try:
            result = fn()

            if asyncio.iscoroutine(result):
                try:
                    asyncio.get_running_loop()
                    import threading

                    res_val = None
                    exc_val = None

                    def _worker():
                        nonlocal res_val, exc_val
                        try:
                            res_val = asyncio.run(result)  # pyright: ignore[reportArgumentType]
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
            end = time.monotonic()
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
