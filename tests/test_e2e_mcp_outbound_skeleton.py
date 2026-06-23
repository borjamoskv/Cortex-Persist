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


# ── MCP Outbound Skeleton Tests ──


class TestMCPOutbound:
    """Test MCP outbound client skeleton."""

    def test_client_initialization(self):
        """Client initializes with empty tool list."""
        from babylon60.pipeline.mcp_outbound import MCPOutboundClient

        client = MCPOutboundClient()
        assert client.available_tools == []
        assert client.get_tool_schemas_for_prompt() == ""

    def test_client_call_unknown_tool(self):
        """Calling unknown tool returns error dict."""
        import asyncio

        from babylon60.pipeline.mcp_outbound import MCPOutboundClient

        client = MCPOutboundClient()
        result = asyncio.run(client.call_tool("nonexistent", {}))
        assert "error" in result
        assert "not found" in result["error"]

    def test_tool_spec_dataclass(self):
        """MCPToolSpec holds tool metadata correctly."""
        from babylon60.pipeline.mcp_outbound import MCPToolSpec

        spec = MCPToolSpec(
            name="web_search",
            description="Search the web",
            input_schema={"query": {"type": "string"}},
            server_name="brave",
        )
        assert spec.name == "web_search"
        assert spec.server_name == "brave"

    def test_tool_schema_formatting(self):
        """Tool schemas format correctly for prompt injection."""
        from babylon60.pipeline.mcp_outbound import MCPOutboundClient, MCPToolSpec

        client = MCPOutboundClient()
        client._tools = [
            MCPToolSpec(name="search", description="Web search"),
            MCPToolSpec(name="read", description="Read file"),
        ]
        schema_text = client.get_tool_schemas_for_prompt()
        assert "<available_tools>" in schema_text
        assert "search" in schema_text
        assert "read" in schema_text
