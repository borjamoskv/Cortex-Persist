import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from cortex.pipeline.mcp_outbound import MCPOutboundClient, MCPToolSpec

@pytest.fixture
def server_configs():
    return [
        {
            "name": "test-server",
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "mcp_server_test"]
        },
        {
            "name": "sse-server",
            "transport": "sse",
            "url": "http://localhost:8000/sse"
        }
    ]

@pytest.mark.asyncio
async def test_client_initialization_and_discovery(server_configs):
    # Mocking MCP SDK components
    mock_tools_response = MagicMock()
    mock_tool = MagicMock()
    mock_tool.name = "get_weather"
    mock_tool.description = "Get weather info"
    mock_tool.inputSchema = {"city": {"type": "string"}}
    mock_tools_response.tools = [mock_tool]

    mock_session = AsyncMock()
    mock_session.list_tools.return_value = mock_tools_response
    mock_session.initialize = AsyncMock()

    with patch("cortex.pipeline.mcp_outbound.stdio_client", return_value=AsyncMock()) as mock_stdio, \
         patch("cortex.pipeline.mcp_outbound.sse_client", return_value=AsyncMock()) as mock_sse, \
         patch("cortex.pipeline.mcp_outbound.ClientSession", return_value=mock_session):

        client = MCPOutboundClient(server_configs)
        await client.initialize()

        assert client._initialized is True
        assert len(client.available_tools) == 2
        assert client.available_tools[0].name == "test-server:get_weather"
        assert client.available_tools[1].name == "sse-server:get_weather"

        # Verify prefixing
        assert "test-server" in client._sessions
        assert "sse-server" in client._sessions

@pytest.mark.asyncio
async def test_call_tool_routing(server_configs):
    mock_session_1 = AsyncMock()
    mock_session_2 = AsyncMock()

    mock_tool_1 = MagicMock()
    mock_tool_1.name = "tool1"
    mock_tool_1.description = "desc1"
    mock_tool_1.inputSchema = {}

    mock_tool_2 = MagicMock()
    mock_tool_2.name = "tool2"
    mock_tool_2.description = "desc2"
    mock_tool_2.inputSchema = {}

    client = MCPOutboundClient(server_configs)
    client._initialized = True
    client._sessions = {
        "test-server": mock_session_1,
        "sse-server": mock_session_2
    }
    client._tools = [
        MCPToolSpec(name="test-server:tool1", description="desc1", server_name="test-server"),
        MCPToolSpec(name="sse-server:tool2", description="desc2", server_name="sse-server")
    ]

    # Mock success responses
    mock_result = MagicMock()
    item = MagicMock()
    item.text = "result text"
    mock_result.content = [item]
    mock_result.isError = False

    mock_session_1.call_tool.return_value = mock_result

    # Call tool 1
    resp = await client.call_tool("test-server:tool1", {"arg": 1})

    assert resp["tool"] == "tool1"
    assert resp["server"] == "test-server"
    assert resp["content"][0]["text"] == "result text"
    mock_session_1.call_tool.assert_called_once_with("tool1", {"arg": 1})
    mock_session_2.call_tool.assert_not_called()

@pytest.mark.asyncio
async def test_call_tool_not_found():
    client = MCPOutboundClient([])
    resp = await client.call_tool("missing:tool", {})
    assert resp["isError"] is True
    assert "not found" in resp["error"]

@pytest.mark.asyncio
async def test_call_tool_error_handling():
    mock_session = AsyncMock()
    client = MCPOutboundClient([{"name": "err-server"}])
    client._sessions = {"err-server": mock_session}
    client._tools = [MCPToolSpec(name="err-server:fail", description="", server_name="err-server")]

    # Mock protocol error
    from mcp import McpError
    mock_session.call_tool.side_effect = McpError("Protocol failed")

    resp = await client.call_tool("err-server:fail", {})
    assert resp["isError"] is True
    assert "MCP Protocol Error" in resp["error"]

    # Mock timeout
    mock_session.call_tool.side_effect = asyncio.TimeoutError()
    resp = await client.call_tool("err-server:fail", {})
    assert resp["isError"] is True
    assert "timed out" in resp["error"]

@pytest.mark.asyncio
async def test_close_cleans_up():
    client = MCPOutboundClient([])
    client._exit_stack = AsyncMock()
    client._initialized = True
    client._sessions = {"s": AsyncMock()}
    client._tools = [MCPToolSpec(name="t", description="", server_name="s")]

    await client.close()

    client._exit_stack.aclose.assert_called_once()
    assert client._initialized is False
    assert len(client._sessions) == 0
    assert len(client.available_tools) == 0
