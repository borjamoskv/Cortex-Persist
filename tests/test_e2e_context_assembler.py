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


# ── Context Assembler Tests ──


class TestContextAssembler:
    """Test the unified context assembler."""

    def test_empty_assembly(self):
        assembler = ContextAssembler()
        ctx = assembler.assemble(intent="test query")
        assert isinstance(ctx, ContextPacket)
        assert ctx.total_tokens == 0

    def test_hint_resolution_missing_ki(self):
        assembler = ContextAssembler()
        ctx = assembler.assemble(intent="test", hints=["nonexistent_ki_12345"])
        assert len(ctx.knowledge_items) == 0  # Should not crash
