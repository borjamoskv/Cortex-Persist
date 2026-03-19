"""Tests for the MCP Client integration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.agents.mcp_client import McpConnectionManager, McpToolWrapper, register_mcp_tools
from cortex.agents.mcp_config import McpServerConfig, load_mcp_config
from cortex.agents.tools import ToolRegistry


@dataclass
class MockMcpResult:
    isError: bool
    content: list[MockMcpContent]


@dataclass
class MockMcpContent:
    text: str


@dataclass
class MockMcpTool:
    name: str
    description: str


@pytest.mark.asyncio
async def test_mcp_tool_wrapper_success():
    """Verify that a successful MCP tool call maps to CORTEX tool output."""
    mock_session = AsyncMock()
    mock_session.call_tool.return_value = MockMcpResult(
        isError=False,
        content=[MockMcpContent(text="Successfully checked out branch main")],
    )

    wrapper = McpToolWrapper(
        session=mock_session,
        name="mcp_git_checkout",
        original_name="checkout",
    )

    assert wrapper.name == "mcp_git_checkout"

    result = await wrapper.execute(branch="main")
    
    mock_session.call_tool.assert_called_once_with("checkout", arguments={"branch": "main"})
    
    assert result["success"] is True
    assert result["output"] == "Successfully checked out branch main"
    assert result["mcp_meta"]["isError"] is False


@pytest.mark.asyncio
async def test_mcp_tool_wrapper_error():
    """Verify that a failed MCP tool call maps to a CORTEX failure."""
    mock_session = AsyncMock()
    mock_session.call_tool.return_value = MockMcpResult(
        isError=True,
        content=[MockMcpContent(text="Branch not found")],
    )

    wrapper = McpToolWrapper(
        session=mock_session,
        name="mcp_git_checkout",
        original_name="checkout",
    )

    result = await wrapper.execute(branch="main")
    
    assert result["success"] is False
    assert result["output"] == "Branch not found"
    assert result["mcp_meta"]["isError"] is True


@pytest.mark.asyncio
async def test_register_mcp_tools():
    """Verify that tools from an active session are registered to ToolRegistry."""
    mock_registry = ToolRegistry()
    
    mock_manager = MagicMock(spec=McpConnectionManager)
    mock_manager.config = McpServerConfig(name="stripe", command="npx", args=["-y", "@stripe/mcp"])
    
    mock_session = AsyncMock()
    
    mock_response = MagicMock()
    mock_response.tools = [
        MockMcpTool(name="charge", description="Create a charge"),
        MockMcpTool(name="refund", description="Refund a charge"),
    ]
    mock_session.list_tools.return_value = mock_response
    mock_manager.session = mock_session

    await register_mcp_tools(mock_registry, mock_manager)

    # They should be prefixed
    assert mock_registry.has("mcp_stripe_charge")
    assert mock_registry.has("mcp_stripe_refund")
    assert len(mock_registry) == 2


def test_load_mcp_config(tmp_path: Path):
    """Verify mcp config loading behaves gracefully."""
    config_file = tmp_path / "mcp_servers.json"
    
    # 1. Test missing file
    assert load_mcp_config(str(config_file)) == []

    # 2. Test valid file
    config_data = {
        "mcpServers": {
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "ghp_123"}
            }
        }
    }
    config_file.write_text(json.dumps(config_data))
    
    configs = load_mcp_config(str(config_file))
    assert len(configs) == 1
    assert configs[0].name == "github"
    assert configs[0].command == "npx"
    assert configs[0].args == ["-y", "@modelcontextprotocol/server-github"]
    assert configs[0].env["GITHUB_TOKEN"] == "ghp_123"
