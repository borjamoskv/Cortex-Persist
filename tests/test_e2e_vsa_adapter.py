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


# ── VSA Adapter Tests ──


class TestVSAAdapter:
    """Test VSA context adapter integration."""

    def test_adapter_graceful_when_unavailable(self):
        """Adapter returns empty results when VSA engine not importable."""
        from babylon60.context.vsa_adapter import VSAContextAdapter

        adapter = VSAContextAdapter.__new__(VSAContextAdapter)
        adapter._available = False
        adapter._mem = None
        adapter._agent_id = "test"
        adapter._D = 10000
        adapter._decay_lambda = 0.05
        adapter._memory_dir = None

        results = adapter.query("test query")
        assert results == []
        assert adapter.ingest("test") is False
        report = adapter.consolidate()
        assert report["persisted"] is False

    def test_adapter_diagnostics_unavailable(self):
        """Diagnostics report unavailable state."""
        from babylon60.context.vsa_adapter import VSAContextAdapter

        adapter = VSAContextAdapter.__new__(VSAContextAdapter)
        adapter._available = False
        adapter._mem = None
        adapter._agent_id = "test"
        adapter._D = 10000
        adapter._decay_lambda = 0.05
        adapter._memory_dir = None

        diag = adapter.diagnostics()
        assert diag["available"] is False

    def test_assembler_with_vsa_bridge(self):
        """ContextAssembler uses VSA bridge when provided."""

        class MockVSA:
            def query(self, intent, top_k=3):
                return [
                    {
                        "id": "vsa-0",
                        "content": "algebraic context",
                        "similarity": 0.85,
                        "tags": {},
                        "timestamp": 0,
                    }
                ]

        assembler = ContextAssembler(vsa_adapter=MockVSA())
        ctx = assembler.assemble(intent="test vsa")
        # VSA results should appear in knowledge_items
        assert any(ki.get("method") == "vsa" for ki in ctx.knowledge_items), (
            f"Expected VSA items in: {ctx.knowledge_items}"
        )
