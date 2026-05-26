"""CORTEX Pipeline — MCP Outbound Client (Skeleton).

Adapter enabling the AgentExecutor to call external MCP tools during
execution. Phase 2b will implement the full tool-call parsing loop.

∴ Reality: C5-REAL (interface defined, integration pending)
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

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

    Phase 2b: Full tool-call loop with response parsing.
    Current: Tool discovery and schema injection only.
    """

    def __init__(self, server_configs: list[dict[str, Any]] | None = None):
        self._server_configs = server_configs or []
        self._tools: list[MCPToolSpec] = []
        self._initialized = False
        self._exit_stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}

    async def initialize(self) -> None:
        """Connect to configured MCP servers and discover tools."""
        if self._initialized:
            return

        for config in self._server_configs:
            server_name = config.get("name", "unknown")
            try:
                tools = await self._discover_tools(config)
                self._tools.extend(tools)
                logger.info(
                    "[MCP-OUT] Discovered %d tools from %s",
                    len(tools),
                    server_name,
                )
            except (asyncio.TimeoutError, ConnectionError, Exception) as e:
                logger.warning(
                    "[MCP-OUT] Failed to connect to %s: %s",
                    server_name,
                    e,
                )

        self._initialized = True

    async def _discover_tools(self, config: dict[str, Any]) -> list[MCPToolSpec]:
        """Discover tools from a single MCP server.

        Integrates with real MCP client SDK to establish connections
        and retrieve tool schemas.
        """
        server_name = config.get("name", "unknown")
        transport_type = config.get("transport", "stdio")

        if transport_type == "stdio":
            command = config.get("command")
            args = config.get("args", [])
            env = config.get("env")
            if not command:
                raise ValueError(f"Missing 'command' for stdio transport in {server_name}")

            server_params = StdioServerParameters(command=command, args=args, env=env)
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
        elif transport_type == "sse":
            url = config.get("url")
            if not url:
                raise ValueError(f"Missing 'url' for sse transport in {server_name}")
            read_stream, write_stream = await self._exit_stack.enter_async_context(sse_client(url))
        else:
            raise ValueError(f"Unsupported transport: {transport_type}")

        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        self._sessions[server_name] = session

        # Fetch tools with a timeout to avoid hanging the pipeline
        try:
            response = await asyncio.wait_for(session.list_tools(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("[MCP-OUT] Timeout listing tools from %s", server_name)
            return []

        specs = []
        for tool in response.tools:
            # Prefix tool name with server name to ensure uniqueness
            # Format: 'server_name:tool_name'
            prefixed_name = f"{server_name}:{tool.name}"
            specs.append(
                MCPToolSpec(
                    name=prefixed_name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema or {},
                    server_name=server_name,
                )
            )
        return specs

    @property
    def available_tools(self) -> list[MCPToolSpec]:
        """Return all discovered tools across connected servers."""
        return list(self._tools)

    def get_tool_schemas_for_prompt(self) -> str:
        """Format tool schemas for injection into system prompts.

        Returns a structured block that agents can parse to know
        which tools are available for delegation.
        """
        if not self._tools:
            return ""

        lines = ["<available_tools>"]
        for tool in self._tools:
            lines.append(f"  - name: {tool.name}")
            lines.append(f"    description: {tool.description}")
            if tool.input_schema:
                import json

                lines.append(f"    schema: {json.dumps(tool.input_schema)}")
        lines.append("</available_tools>")
        return "\n".join(lines)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool by name.

        Dispatches the tool call to the correct server based on the
        prefixed tool name.
        """
        matching = [t for t in self._tools if t.name == name]
        if not matching:
            logger.warning("[MCP-OUT] Tool '%s' not found", name)
            return {
                "isError": True,
                "error": f"Tool '{name}' not found",
                "available": [t.name for t in self._tools],
            }

        tool_spec = matching[0]
        server_name = tool_spec.server_name
        session = self._sessions.get(server_name)

        if not session:
            logger.error("[MCP-OUT] Session for server '%s' not found", server_name)
            return {
                "isError": True,
                "error": f"Connection to server '{server_name}' lost or not initialized",
            }

        # Strip prefix before sending to the server
        original_name = name.split(":", 1)[-1] if ":" in name else name

        logger.info("[MCP-OUT] Calling tool '%s' on server '%s'", original_name, server_name)

        try:
            from mcp import McpError

            result = await asyncio.wait_for(
                session.call_tool(original_name, arguments), timeout=30.0
            )

            # Format result content
            content = []
            for item in result.content:
                if hasattr(item, "text"):
                    content.append({"type": "text", "text": item.text})
                elif hasattr(item, "data"):
                    content.append({"type": "base64", "data": item.data, "mimeType": item.mimeType})

            return {
                "content": content,
                "isError": getattr(result, "isError", False),
                "server": server_name,
                "tool": original_name,
            }

        except asyncio.TimeoutError:
            logger.error("[MCP-OUT] Timeout calling tool '%s' on '%s'", original_name, server_name)
            return {
                "isError": True,
                "error": f"Tool execution timed out: {name}",
            }
        except McpError as e:
            logger.error("[MCP-OUT] MCP Error from %s: %s", server_name, e)
            return {
                "isError": True,
                "error": f"MCP Protocol Error: {e}",
            }
        except Exception as e:
            logger.error("[MCP-OUT] Unexpected error calling tool %s: %s", name, e)
            return {
                "isError": True,
                "error": f"Internal Error: {e}",
            }

    async def close(self) -> None:
        """Disconnect from all MCP servers."""
        logger.info("[MCP-OUT] Closing all MCP sessions...")
        await self._exit_stack.aclose()
        self._sessions.clear()
        self._tools.clear()
        self._initialized = False
