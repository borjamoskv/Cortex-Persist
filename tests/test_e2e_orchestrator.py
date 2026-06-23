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


# ── Orchestrator Tests ──


class TestOrchestrator:
    """Test the E2E orchestrator pipeline flow."""

    def test_basic_pipeline_success(self):
        orch = CortexOrchestrator()
        req = PipelineRequest(intent="hello world")
        result = orch.run(req)

        assert result.status == PipelineStatus.SUCCESS
        assert result.mission_id == req.mission_id
        assert result.latency_ms > 0
        assert result.ledger_hash != ""
        assert len(result.stages) == 6  # All 6 stages should run

    def test_empty_intent_fails(self):
        orch = CortexOrchestrator()
        req = PipelineRequest(intent="")
        result = orch.run(req)

        assert result.status == PipelineStatus.FAILED
        assert "Empty intent" in result.error

    def test_zero_budget_fails(self):
        orch = CortexOrchestrator()
        req = PipelineRequest(intent="test", budget_limit_usd=0)
        result = orch.run(req)

        assert result.status == PipelineStatus.FAILED
        assert "Budget" in result.error

    def test_pipeline_with_context_assembler(self):
        assembler = ContextAssembler()  # No backends
        orch = CortexOrchestrator(context_assembler=assembler)
        req = PipelineRequest(intent="analyze security patterns")
        result = orch.run(req)

        assert result.status == PipelineStatus.SUCCESS
        assert len(result.stages) == 6

    def test_pipeline_with_router(self):
        router = AgentRouter()
        orch = CortexOrchestrator(agent_router=router)
        req = PipelineRequest(intent="find vulnerability in smart contract")
        result = orch.run(req)

        assert result.status == PipelineStatus.SUCCESS
        assert "security-analyst" in result.agent_chain

    def test_pipeline_with_delivery(self):
        delivery = DeliveryManager()
        orch = CortexOrchestrator(delivery_manager=delivery)
        req = PipelineRequest(
            intent="test delivery",
            delivery=DeliveryTarget(type=DeliveryType.MEMORY),
        )
        result = orch.run(req)
        assert result.status == PipelineStatus.SUCCESS

    def test_full_pipeline_all_components(self):
        orch = CortexOrchestrator(
            context_assembler=ContextAssembler(),
            agent_router=AgentRouter(),
            delivery_manager=DeliveryManager(),
        )
        req = PipelineRequest(
            intent="research state of the art in formal verification",
            context_hints=[],
            delivery=DeliveryTarget(type=DeliveryType.MEMORY),
        )
        result = orch.run(req)

        assert result.status == PipelineStatus.SUCCESS
        assert result.cost_usd >= 0
        assert result.ledger_hash
        assert len(result.stages) == 6
        assert all(s.latency_ms >= 0 for s in result.stages)
