# [C5-REAL] Exergy-Maximized
"""CORTEX Pipeline - MCP Outbound Client.

Adapter enabling the AgentExecutor to call external MCP tools during
execution. Connects to one or more MCP servers (stdio or SSE) and
dispatches tool calls.

∴ Reality: C5-REAL (full implementation)
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

logger = logging.getLogger("cortex.pipeline.mcp_outbound")


@dataclass
class MCPToolSpec:
    """Descriptor for an available MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


class MCPOutboundClient:
    """Outbound MCP client for executor tool delegation.

    Connects the pipeline executor to external MCP servers,
    enabling agents to invoke tools (web search, file ops, etc.)
    during inference.
    """

    def __init__(self, server_configs: list[dict[str, Any]] | None = None):
        """Initialize with a list of server configurations.

        Config schema:
        {
            "name": "brave-search",
            "transport": "stdio",  # or "sse"
            "command": "npx",      # for stdio
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {"BRAVE_API_KEY": "..."},
            "url": "http://localhost:8080/sse" # for sse
        }
        """
        self._server_configs = server_configs or []
        self._tools: list[MCPToolSpec] = []
        self._sessions: dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
        self._initialized = False

    async def initialize(self) -> None:
        """Connect to configured MCP servers and discover tools."""
        if self._initialized:
            return

        for config in self._server_configs:
            server_name = config.get("name", "unknown")
            try:
                tools = await self._connect_to_server(config)
                self._tools.extend(tools)
                logger.info(
                    "[MCP-OUT] Discovered %d tools from %s",
                    len(tools),
                    server_name,
                )
            except (ValueError, TypeError, OSError, RuntimeError, ConnectionError) as e:
                logger.exception(
                    "[MCP-OUT] Failed to connect to %s: %s",
                    server_name,
                    e,
                )

        self._initialized = True

    async def _connect_to_server(self, config: dict[str, Any]) -> list[MCPToolSpec]:
        """Connect to a single MCP server and return its tools."""
        server_name = config.get("name", "unknown")
        transport_type = config.get("transport", "stdio")

        if transport_type == "stdio":
            command = config.get("command")
            if not command:
                raise ValueError(f"Missing 'command' for stdio server {server_name}")

            params = StdioServerParameters(
                command=command, args=config.get("args", []), env=config.get("env")
            )

            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

        elif transport_type == "sse":
            url = config.get("url")
            if not url:
                raise ValueError(f"Missing 'url' for SSE server {server_name}")

            read_stream, write_stream = await self._exit_stack.enter_async_context(sse_client(url))
            session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

        # Initialize session
        await session.initialize()
        self._sessions[server_name] = session

        # Discover tools
        response = await session.list_tools()
        tools = []
        for tool in response.tools:
            tools.append(
                MCPToolSpec(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema,
                    server_name=server_name,
                )
            )
        return tools

    @property
    def available_tools(self) -> list[MCPToolSpec]:
        """Return all discovered tools across connected servers."""
        return list(self._tools)

    def get_tool_schemas_for_prompt(self) -> str:
        """Format tool schemas for injection into system prompts."""
        if not self._tools:
            return ""

        lines = ["<available_tools>"]
        for tool in self._tools:
            lines.append(f"  - name: {tool.name}")
            lines.append(f"    description: {tool.description}")
            if tool.input_schema:
                lines.append(f"    schema: {json.dumps(tool.input_schema)}")
        lines.append("</available_tools>")
        return "\n".join(lines)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool by name."""
        matching = [t for t in self._tools if t.name == name]
        if not matching:
            return {
                "error": f"Tool '{name}' not found",
                "available": [t.name for t in self._tools],
            }

        tool_spec = matching[0]
        session = self._sessions.get(tool_spec.server_name)

        if not session:
            return {"error": f"Session for server '{tool_spec.server_name}' not found"}

        logger.info("[MCP-OUT] Calling tool %s on %s", name, tool_spec.server_name)
        try:
            # We wrap the call in a timeout to avoid hanging the pipeline
            result = await asyncio.wait_for(session.call_tool(name, arguments), timeout=30.0)

            # MCP ToolResult can contain multiple content blocks
            return {
                "content": [
                    {"type": getattr(c, "type", "text"), "text": getattr(c, "text", str(c))}
                    for c in result.content
                ],
                "is_error": result.isError,
            }
        except asyncio.TimeoutError:
            logger.error("[MCP-OUT] Timeout calling tool %s", name)
            return {"error": f"Timeout calling tool {name}"}
        except (ValueError, TypeError, OSError, RuntimeError, ConnectionError) as e:
            logger.exception("[MCP-OUT] Error calling tool %s: %s", name, e)
            return {"error": f"Error calling tool {name}"}

    async def close(self) -> None:
        """Disconnect from all MCP servers."""
        await self._exit_stack.aclose()
        self._tools.clear()
        self._sessions.clear()
        self._initialized = False
