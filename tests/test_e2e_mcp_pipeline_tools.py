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


# ── MCP Pipeline Tools Tests ──


class TestMCPPipelineTools:
    """Test MCP pipeline tool serialization."""

    def test_result_to_dict_single_agent(self):
        from cortex.mcp.pipeline_tools import _result_to_dict

        result = PipelineResult(
            mission_id="m-test",
            status=PipelineStatus.SUCCESS,
            output={"content": "hello", "provider": "gemini"},
            ledger_hash="abc123",
            completed_at=1.0,
        )
        d = _result_to_dict(result)
        assert d["content"] == "hello"
        assert d["provider"] == "gemini"
        assert d["status"] == "success"

    def test_result_to_dict_multi_agent(self):
        from cortex.mcp.pipeline_tools import _result_to_dict

        result = PipelineResult(
            mission_id="m-multi",
            status=PipelineStatus.SUCCESS,
            output={
                "multi_agent": True,
                "results": [
                    {"agent_id": "a1", "content": "result 1"},
                    {"agent_id": "a2", "content": "result 2"},
                ],
            },
            completed_at=1.0,
        )
        d = _result_to_dict(result)
        assert "[a1]" in d["content"]
        assert "[a2]" in d["content"]

    def test_result_to_dict_error(self):
        from cortex.mcp.pipeline_tools import _result_to_dict

        result = PipelineResult(
            mission_id="m-err",
            status=PipelineStatus.FAILED,
            error="something broke",
            completed_at=1.0,
        )
        d = _result_to_dict(result)
        assert d["status"] == "failed"
        assert d["error"] == "something broke"
