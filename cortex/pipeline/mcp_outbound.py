"""CORTEX Pipeline — MCP Outbound Client (Skeleton).

Adapter enabling the AgentExecutor to call external MCP tools during
execution. Phase 2b will implement the full tool-call parsing loop.

∴ Reality: C5-REAL (interface defined, integration pending)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

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

    async def initialize(self) -> None:
        """Connect to configured MCP servers and discover tools."""
        if self._initialized:
            return
        self._initialized = True

        for config in self._server_configs:
            try:
                tools = await self._discover_tools(config)
                self._tools.extend(tools)
                logger.info(
                    "[MCP-OUT] Discovered %d tools from %s",
                    len(tools),
                    config.get("name", "unknown"),
                )
            except Exception as e:
                logger.warning(
                    "[MCP-OUT] Failed to connect to %s: %s",
                    config.get("name", "unknown"),
                    e,
                )

    async def _discover_tools(self, config: dict[str, Any]) -> list[MCPToolSpec]:
        """Discover tools from a single MCP server.

        Phase 2b: Real MCP client SDK integration.
        Current: Returns empty list (discovery skeleton).
        """
        # TODO(Phase 2b): Use mcp.ClientSession to connect and list_tools()
        return []

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

        Phase 2b: Real dispatch to the appropriate MCP server.
        Current: Returns structured error indicating tool-call not yet wired.
        """
        matching = [t for t in self._tools if t.name == name]
        if not matching:
            return {
                "error": f"Tool '{name}' not found",
                "available": [t.name for t in self._tools],
            }

        # TODO(Phase 2b): Route to the correct server and execute
        return {
            "error": "Tool execution not yet implemented (Phase 2b)",
            "tool": name,
            "arguments": arguments,
        }

    async def close(self) -> None:
        """Disconnect from all MCP servers."""
        self._tools.clear()
        self._initialized = False
