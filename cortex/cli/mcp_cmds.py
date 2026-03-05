"""CORTEX MCP Module CLI commands.

Registered under `cortex mcp`.
"""

from __future__ import annotations

import click
import logging
from cortex.cli.common import cli, console

logger = logging.getLogger("cortex.cli.mcp")

@cli.group("mcp")
def mcp_cmds() -> None:
    """Model Context Protocol (MCP) integrations."""
    pass

@mcp_cmds.command("jules")
@click.option("--host", default="127.0.0.1", help="Transport host")
@click.option("--port", default=5001, type=int, help="SSE port")
@click.option("--transport", default="sse", type=click.Choice(["sse", "stdio"]), help="Transport protocol")
def jules_mcp(host: str, port: int, transport: str) -> None:
    """Boot the MOSKV-Jules Sovereign MCP Server (Gemini 3)."""
    try:
        from cortex.mcp.jules_server import run_jules_mcp
    except ImportError:
        console.print("[red]❌ Error: MCP SDK not installed. Run: pip install 'mcp'[/red]")
        return
        
    console.print(f"[bold blue]🚀 Booting CORTEX Jules MCP Server (Transport: {transport}...)[/bold blue]")
    if transport == "sse":
        console.print(f"[dim]Listening on http://{host}:{port}/sse[/dim]")
        
    run_jules_mcp(host=host, port=port, transport=transport)

@mcp_cmds.command("trust")
@click.option("--host", default="127.0.0.1", help="Transport host")
@click.option("--port", default=5002, type=int, help="SSE port")
@click.option("--transport", default="sse", type=click.Choice(["sse", "stdio"]), help="Transport protocol")
def trust_mcp(host: str, port: int, transport: str) -> None:
    """Boot the standard CORTEX Trust MCP Server."""
    from cortex.mcp.server import run_server
    from cortex.mcp.utils import MCPServerConfig
    
    cfg = MCPServerConfig(host=host, port=port, transport=transport) # type: ignore
    run_server(cfg)
