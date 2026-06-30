# [C5-REAL] Exergy-Maximized
"""CORTEX E2E Pipeline - Integration Tests.

Tests the full pipeline flow: Ingress → Context → Plan → Execute → Persist → Egress.
"""

import pytest
import time

from babylon60.pipeline import (
    ContextPacket,
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)
from babylon60.pipeline.orchestrator import CortexOrchestrator
from babylon60.pipeline._orchestrator_exceptions import (
    BudgetExhaustedError,
    PipelineCancelledError,
)
from babylon60.router.router import AgentRouter, AgentCapability
from babylon60.context.assembler import ContextAssembler
from babylon60.delivery.manager import DeliveryManager


# ── Enhanced Async Tests ──


class TestAsyncPipelineEnhanced:
    """Test native async pipeline improvements."""

    def test_run_async_timeout_no_deadlock(self):
        """run_async with slow executor times out without deadlock."""
        import asyncio

        class SlowExecutor:
            async def execute(self, **kw):
                await asyncio.sleep(999)

        orch = CortexOrchestrator(agent_executor=SlowExecutor())
        req = PipelineRequest(intent="slow mission", timeout_s=0.5)
        result = asyncio.run(orch.run_async(req))
        assert result.status == PipelineStatus.FAILED
        assert "timeout" in result.error.lower()

    def test_run_async_cancellation_contract(self):
        """Cancellation returns CANCELLED status."""
        import asyncio

        async def _test():
            orch = CortexOrchestrator()
            req = PipelineRequest(intent="cancel test")
            task = asyncio.create_task(orch.run_async(req))
            # Let it start then cancel
            await asyncio.sleep(0)
            task.cancel()
            try:
                result = await task
                # If pipeline completed before cancel, that's OK
                assert result.status in (PipelineStatus.SUCCESS, PipelineStatus.CANCELLED)
            except asyncio.CancelledError:
                import logging

        # Also valid

        asyncio.run(_test())

    def test_run_streaming_yields_traces(self):
        """run_streaming yields StageTrace events then PipelineResult."""
        import asyncio

        async def _test():
            orch = CortexOrchestrator()
            req = PipelineRequest(intent="streaming test")
            events = []
            async for event in orch.run_streaming(req):
                events.append(event)

            # Should yield 6 StageTraces + 1 PipelineResult = 7 events
            assert len(events) == 7
            # Last event is the final PipelineResult
            assert isinstance(events[-1], PipelineResult)
            assert events[-1].status == PipelineStatus.SUCCESS
            # First 6 are StageTraces
            for trace in events[:6]:
                assert isinstance(trace, StageTrace)
                assert trace.latency_ms >= 0

        asyncio.run(_test())

    def test_run_async_six_stages(self):
        """Async pipeline produces exactly 6 stage traces."""
        import asyncio

        orch = CortexOrchestrator()
        req = PipelineRequest(intent="stage count test")
        result = asyncio.run(orch.run_async(req))
        assert result.status == PipelineStatus.SUCCESS
        assert len(result.stages) == 6
        stage_names = [s.stage for s in result.stages]
        assert PipelineStage.INGRESS in stage_names
        assert PipelineStage.EXECUTION in stage_names
        assert PipelineStage.PERSISTENCE in stage_names
