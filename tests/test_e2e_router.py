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


# ── Router Tests ──


class TestAgentRouter:
    """Test deterministic agent routing."""

    def test_security_routing(self):
        router = AgentRouter()
        plan = router.route("find vulnerability in smart contract")
        assert "security-analyst" in plan["agents"]

    def test_code_routing(self):
        router = AgentRouter()
        plan = router.route("implement a Python class for data processing")
        assert "code-engineer" in plan["agents"]

    def test_research_routing(self):
        router = AgentRouter()
        plan = router.route("research the state of the art in LLM evaluation")
        assert "researcher" in plan["agents"]

    def test_fallback_to_general(self):
        router = AgentRouter()
        plan = router.route("what time is it?")
        assert "general" in plan["agents"]

    def test_register_custom_agent(self):
        router = AgentRouter()
        router.register_agent(
            AgentCapability(
                agent_id="audio-engineer",
                patterns=[r"master", r"audio", r"stems", r"loudness"],
                priority=0,
            )
        )
        plan = router.route("master this audio track")
        assert "audio-engineer" in plan["agents"]

    def test_budget_aware_routing(self):
        router = AgentRouter()
        plan = router.route("analyze vulnerability", budget_remaining=0.001)
        assert len(plan["agents"]) >= 1  # Should still route at least one
