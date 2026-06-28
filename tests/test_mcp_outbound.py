# [C5-REAL] Exergy-Maximized

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from cortex.pipeline.mcp_outbound import MCPOutboundClient, MCPToolSpec


@pytest.fixture
def mock_session():
    session = AsyncMock()
    # Mock list_tools response
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool"
    mock_tool.inputSchema = {"type": "object"}

    mock_response = MagicMock()
    mock_response.tools = [mock_tool]
    session.list_tools.return_value = mock_response

    # Mock call_tool response
    mock_content = MagicMock()
    mock_content.type = "text"
    mock_content.text = "tool result"

    mock_call_result = MagicMock()
    mock_call_result.content = [mock_content]
    mock_call_result.isError = False
    session.call_tool.return_value = mock_call_result

    return session


@pytest.mark.asyncio
async def test_mcp_outbound_initialization_stdio(mock_session):
    configs = [
        {
            "name": "test-server",
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "mcp_server"],
        }
    ]

    client = MCPOutboundClient(configs)

    with (
        patch("cortex.pipeline.mcp_outbound.stdio_client", return_value=AsyncMock()) as mock_stdio,
        patch("cortex.pipeline.mcp_outbound.ClientSession", return_value=mock_session),
    ):
        # Mocking the async context managers
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        mock_session.__aenter__.return_value = mock_session

        await client.initialize()

        assert len(client.available_tools) == 1
        assert client.available_tools[0].name == "test_tool"
        assert "test-server" in client._sessions


@pytest.mark.asyncio
async def test_mcp_outbound_routing(mock_session):
    client = MCPOutboundClient()
    client._tools = [
        MCPToolSpec(name="tool1", description="desc1", server_name="server1"),
        MCPToolSpec(name="tool2", description="desc2", server_name="server2"),
    ]

    session1 = AsyncMock()
    session2 = AsyncMock()

    # Mock call results
    res1 = MagicMock()
    res1.content = [MagicMock(type="text", text="res1")]
    res1.isError = False
    session1.call_tool.return_value = res1

    res2 = MagicMock()
    res2.content = [MagicMock(type="text", text="res2")]
    res2.isError = False
    session2.call_tool.return_value = res2

    client._sessions = {"server1": session1, "server2": session2}

    result1 = await client.call_tool("tool1", {"arg": 1})
    assert result1["content"][0]["text"] == "res1"
    session1.call_tool.assert_called_once_with("tool1", {"arg": 1})

    result2 = await client.call_tool("tool2", {"arg": 2})
    assert result2["content"][0]["text"] == "res2"
    session2.call_tool.assert_called_once_with("tool2", {"arg": 2})


@pytest.mark.asyncio
async def test_mcp_outbound_tool_not_found():
    client = MCPOutboundClient()
    result = await client.call_tool("unknown", {})
    assert "error" in result
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_mcp_outbound_timeout(mock_session):
    client = MCPOutboundClient()
    client._tools = [MCPToolSpec(name="slow_tool", description="desc", server_name="server")]

    async def slow_call(*args, **kwargs):
        await asyncio.sleep(2.0)
        return MagicMock()

    mock_session.call_tool.side_effect = slow_call
    client._sessions = {"server": mock_session}

    async def mock_wait_for(coro, timeout):
        coro.close()  # Prevent unawaited coroutine warning
        raise asyncio.TimeoutError()

    with patch("asyncio.wait_for", side_effect=mock_wait_for):
        result = await client.call_tool("slow_tool", {})
        assert "error" in result
        assert "Timeout" in result["error"]


@pytest.mark.asyncio
async def test_mcp_outbound_connection_failure():
    configs = [{"name": "bad-server", "transport": "stdio", "command": "nonexistent"}]
    client = MCPOutboundClient(configs)

    with patch(
        "cortex.pipeline.mcp_outbound.stdio_client", side_effect=RuntimeError("Conn failed")
    ):
        await client.initialize()
        # Should not raise exception but log it and continue
        assert len(client.available_tools) == 0


@pytest.mark.asyncio
async def test_mcp_outbound_error_during_call(mock_session):
    client = MCPOutboundClient()
    client._tools = [MCPToolSpec(name="err_tool", description="desc", server_name="server")]
    mock_session.call_tool.side_effect = RuntimeError("Tool crashed")
    client._sessions = {"server": mock_session}

    result = await client.call_tool("err_tool", {})
    assert "error" in result
    assert "Error calling tool" in result["error"]
