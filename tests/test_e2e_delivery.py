# [C5-REAL] Exergy-Maximized
"""CORTEX E2E Pipeline - Integration Tests.

Tests the full pipeline flow: Ingress → Context → Plan → Execute → Persist → Egress.
"""

import pytest
import time

from legacy_research.pipeline import (
    ContextPacket,
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)
from legacy_research.pipeline.orchestrator import CortexOrchestrator
from legacy_research.pipeline._orchestrator_exceptions import (
    BudgetExhaustedError,
    PipelineCancelledError,
)
from legacy_research.router.router import AgentRouter, AgentCapability
from legacy_research.context.assembler import ContextAssembler
from legacy_research.delivery.manager import DeliveryManager


# ── Delivery Tests ──


class TestDeliveryManager:
    """Test delivery to various targets."""

    def test_memory_delivery(self):
        dm = DeliveryManager()
        result = dm.deliver({"test": True}, DeliveryTarget(type=DeliveryType.MEMORY), "m-test")
        assert result is True

    def test_file_delivery(self, tmp_path):
        dm = DeliveryManager()
        target = DeliveryTarget(
            type=DeliveryType.FILE, path=str(tmp_path / "output.json"), format="json"
        )
        result = dm.deliver({"key": "value"}, target, "m-file-test")
        assert result is True
        assert (tmp_path / "output.json").exists()
        content = (tmp_path / "output.json").read_text()
        assert '"key"' in content

    def test_markdown_conversion(self):
        md = DeliveryManager._to_markdown({"title": "Test", "items": ["a", "b", "c"]})
        assert "# Pipeline Result" in md
        assert "- a" in md

    def test_file_delivery_no_path_fails(self):
        dm = DeliveryManager()
        result = dm.deliver({}, DeliveryTarget(type=DeliveryType.FILE), "m-no-path")
        assert result is False
