"""CORTEX Agent Runtime — MCP Client Bridge.

Provides `McpConnectionManager` to boot and connect to external
MCP servers via stdio, and `McpToolWrapper` to expose their tools
through the CORTEX `Tool` protocol so agents can use them natively.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from cortex.agents.mcp_config import McpServerConfig
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger("cortex.agents.mcp_client")

__all__ = [
    "McpConnectionManager",
    "McpToolWrapper",
    "register_mcp_tools",
]


class McpToolWrapper:
    """Wraps a remote MCP tool to conform to CORTEX Tool protocol."""

    def __init__(self, session: ClientSession, name: str, original_name: str) -> None:
        self._session = session
        self._name = name
        self._original_name = original_name

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, **kwargs: Any) -> Any:
        """Execute the remote MCP tool via the active ClientSession."""
        logger.debug("Executing MCP tool %s (mapped to %s)", self._name, self._original_name)
        result = await self._session.call_tool(self._original_name, arguments=kwargs)
        
        # Determine success from MCP returned result
        is_error = getattr(result, "isError", False)

        # Build output string from content list
        # MCP responses are typically objects with a list of 'content' blocks
        output = ""
        contents = getattr(result, "content", [])
        if contents:
            chunks = []
            for block in contents:
                text = getattr(block, "text", "")
                chunks.append(text)
            output = "\n".join(chunks)
        else:
            output = str(result)

        return {
            "success": not is_error,
            "output": output,
            "mcp_meta": {"isError": is_error},
        }


class McpConnectionManager:
    """Manages the async lifecycle of an MCP stdio server connection."""

    def __init__(self, config: McpServerConfig) -> None:
        self.config = config
        self._server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
        )
        self._stdio_ctx = None
        self._session_ctx = None
        self.session: ClientSession | None = None

    async def __aenter__(self) -> ClientSession:
        """Start the MCP server subprocess and initialize the session."""
        logger.info("Booting MCP server: %s", self.config.name)
        
        self._stdio_ctx = stdio_client(self._server_params)
        read_stream, write_stream = await self._stdio_ctx.__aenter__()

        self._session_ctx = ClientSession(read_stream, write_stream)
        self.session = await self._session_ctx.__aenter__()

        try:
            await self.session.initialize()
            logger.info("Successfully initialized MCP server: %s", self.config.name)
            return self.session
        except Exception as exc:
            logger.error("Failed to initialize MCP session for %s: %s", self.config.name, exc)
            await self.__aexit__(type(exc), exc, exc.__traceback__)
            raise RuntimeError(f"Failed to initialize MCP server {self.config.name}") from exc

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Gracefully close the session and terminate the subprocess."""
        if self._session_ctx:
            try:
                await self._session_ctx.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.debug("Error closing MCP ClientSession: %s", e)
            self._session_ctx = None
            self.session = None

        if self._stdio_ctx:
            try:
                await self._stdio_ctx.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.debug("Error closing MCP stdio transport: %s", e)
            self._stdio_ctx = None

        logger.info("Stopped MCP server: %s", self.config.name)


async def register_mcp_tools(
    registry: ToolRegistry,
    manager: McpConnectionManager,
) -> None:
    """Fetch available tools from an active MCP session and register them.
    
    Tool names are prefixed with `mcp_{server_name}_` to avoid collisions.
    """
    if not manager.session:
        raise RuntimeError("MCP session is not active")

    try:
        tools_response = await manager.session.list_tools()
        tools_list = getattr(tools_response, "tools", [])
    except Exception as exc:
        logger.error("Failed to list tools from MCP server %s: %s", manager.config.name, exc)
        return

    registered_count = 0
    prefix = f"mcp_{manager.config.name}_"

    for tool_def in tools_list:
        original_name = getattr(tool_def, "name", "")
        if not original_name:
            continue
            
        prefixed_name = f"{prefix}{original_name}"
        
        wrapper = McpToolWrapper(
            session=manager.session,
            name=prefixed_name,
            original_name=original_name,
        )
        registry.register(wrapper)
        registered_count += 1

    logger.info(
        "Registered %d tools from MCP server '%s'",
        registered_count,
        manager.config.name,
    )
