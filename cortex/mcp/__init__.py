"""CORTEX MCP Server Package.

Optimized Multi-Transport Implementation.
"""

from cortex.mcp.server import create_mcp_server, run_server
from cortex.mcp.resilient_gateway import create_resilient_gateway, run_resilient_gateway
from cortex.mcp.utils import MCPServerConfig

__all__ = [
    "create_mcp_server",
    "create_resilient_gateway",
    "run_server",
    "run_resilient_gateway",
    "MCPServerConfig",
]
