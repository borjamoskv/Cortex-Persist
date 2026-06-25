# [C5-REAL] Exergy-Maximized
"""CORTEX E2E Pipeline - Integration Tests.

Tests the full pipeline flow: Ingress → Context → Plan → Execute → Persist → Egress.
"""

import pytest
import time

from cortex.pipeline import (
    ContextPacket,
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)
from cortex.pipeline.orchestrator import CortexOrchestrator
from cortex.pipeline._orchestrator_exceptions import (
    BudgetExhaustedError,
    PipelineCancelledError,
)
from cortex.router.router import AgentRouter, AgentCapability
from cortex.context.assembler import ContextAssembler
from cortex.delivery.manager import DeliveryManager


# ── Contract Tests ──


class TestPipelineContracts:
    """Test that pipeline data contracts are well-formed."""

    def test_pipeline_request_defaults(self):
        req = PipelineRequest(intent="analyze this")
        assert req.intent == "analyze this"
        assert req.budget_limit_usd == 0.10
        assert req.mission_id.startswith("m-")
        assert req.tenant_id == "default"
        assert req.priority == 1
        assert req.timeout_s == 120.0

    def test_pipeline_result_latency(self):
        result = PipelineResult(
            mission_id="test-001",
            status=PipelineStatus.SUCCESS,
            created_at=1000.0,
            completed_at=1001.5,
        )
        assert result.latency_ms == 1500.0

    def test_pipeline_result_total_tokens(self):
        result = PipelineResult(
            mission_id="test-002",
            status=PipelineStatus.SUCCESS,
            stages=[
                StageTrace(
                    stage=PipelineStage.CONTEXT,
                    started_at=0,
                    ended_at=1,
                    tokens_in=100,
                    tokens_out=50,
                ),
                StageTrace(
                    stage=PipelineStage.EXECUTION,
                    started_at=1,
                    ended_at=2,
                    tokens_in=200,
                    tokens_out=300,
                ),
            ],
        )
        assert result.total_tokens == 650

    def test_delivery_target_types(self):
        for dt in DeliveryType:
            target = DeliveryTarget(type=dt)
            assert target.type == dt
            assert target.format == "markdown"

    def test_context_packet_empty(self):
        ctx = ContextPacket()
        assert ctx.facts == []
        assert ctx.knowledge_items == []
        assert ctx.total_tokens == 0

    def test_stage_trace_latency_auto(self):
        trace = StageTrace(stage=PipelineStage.INGRESS, started_at=100.0, ended_at=100.05)
        assert abs(trace.latency_ms - 50.0) < 1.0
