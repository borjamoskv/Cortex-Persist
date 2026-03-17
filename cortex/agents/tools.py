"""CORTEX Agent Runtime — Tool Protocol & Registry.

Tools are atomic capabilities (skills) that agents invoke.
The registry enforces manifest policy: an agent can only
use tools declared in its manifest.tools_allowed.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger("cortex.agents.tools")


@runtime_checkable
class Tool(Protocol):
    """Protocol for an atomic tool/skill."""

    @property
    def name(self) -> str: ...

    async def execute(self, **kwargs: Any) -> Any: ...


class ToolRegistry:
    """Registry of available tools with policy enforcement.

    Agents declare allowed tools in their AgentManifest.
    The registry enforces that agents only access permitted tools.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool by its name."""
        if tool.name in self._tools:
            logger.warning("Tool '%s' already registered, overwriting", tool.name)
        self._tools[tool.name] = tool
        logger.debug("Tool registered: %s", tool.name)

    def get(self, name: str, *, allowed: Optional[list[str]] = None) -> Tool:
        """Retrieve a tool by name, optionally enforcing policy.

        Args:
            name: Tool name to look up.
            allowed: If provided, the tool must be in this allowlist.
                     Typically comes from AgentManifest.tools_allowed.

        Raises:
            KeyError: If tool not found.
            PermissionError: If tool not in allowlist.
        """
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")

        if allowed is not None and name not in allowed:
            raise PermissionError(f"Tool '{name}' is not in the agent's allowed tools: {allowed}")

        return self._tools[name]

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def __len__(self) -> int:
        return len(self._tools)
