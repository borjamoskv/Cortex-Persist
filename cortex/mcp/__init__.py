"""CORTEX MCP Server Package.

Optimized Multi-Transport Implementation.
Uses __getattr__ lazy loading (PEP 562) to avoid pulling in
optional dependencies like markdownify on package import.
"""

from __future__ import annotations

import importlib

__all__ = [
    "MCPServerConfig",
    "create_mcp_server",
    "create_resilient_gateway",
    "run_resilient_gateway",
    "run_server",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "create_resilient_gateway": ("cortex.mcp.resilient_gateway", "create_resilient_gateway"),
    "run_resilient_gateway": ("cortex.mcp.resilient_gateway", "run_resilient_gateway"),
    "create_mcp_server": ("cortex.mcp.server", "create_mcp_server"),
    "run_server": ("cortex.mcp.server", "run_server"),
    "MCPServerConfig": ("cortex.mcp.utils", "MCPServerConfig"),
}


def __getattr__(name: str) -> object:
    """Lazy-load MCP symbols on first access (PEP 562)."""
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.mcp' has no attribute {name!r}")
