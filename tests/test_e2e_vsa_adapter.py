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

    def test_vsa_bridge_basic_flow(self):
        """Test basic query, ingest, and persist flow of VSAPipelineBridge."""
        from babylon60.memory.vsa import VSAPipelineBridge

        bridge = VSAPipelineBridge(agent_id="test_agent_temp")
        rid = bridge.ingest("algebraic context test", record_id="vsa-test-1")
        assert rid == "vsa-test-1"

        results = bridge.query("algebraic context")
        assert len(results) > 0
        assert results[0]["id"] == "vsa-test-1"
        assert results[0]["content"] == "algebraic context test"

        # Persist and clean up
        hash_val = bridge.persist()
        assert len(hash_val) > 0
        
        # Clean up files created
        if bridge._memory._persistence_path.exists():
            bridge._memory._persistence_path.unlink()

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
