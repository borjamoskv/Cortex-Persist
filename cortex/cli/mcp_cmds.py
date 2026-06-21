# [C5-REAL] Exergy-Maximized
"""CORTEX MCP Module CLI commands.

Registered under `cortex mcp`.
"""

from __future__ import annotations

import logging

import click

from cortex.cli.common import cli, console

logger = logging.getLogger("cortex.cli.mcp")


@cli.group("mcp")
def mcp_cmds() -> None:
    """Model Context Protocol (MCP) integrations."""


@mcp_cmds.command("aether")
@click.option("--host", default="127.0.0.1", help="Transport host")
@click.option("--port", default=5001, type=int, help="SSE port")
@click.option(
    "--transport", default="sse", type=click.Choice(["sse", "stdio"]), help="Transport protocol"
)
def aether_mcp(host: str, port: int, transport: str) -> None:
    """Boot the MOSKV-Aether Sovereign MCP Server."""
    try:
        from cortex.mcp.aether_server import run_aether_mcp
    except ImportError:
        console.print("[red]❌ Error: MCP SDK not installed. Run: pip install 'mcp'[/red]")
        return

    console.print(
        f"[bold blue]🚀 Booting CORTEX Aether MCP Server (Transport: {transport}...)[/bold blue]"
    )
    if transport == "sse":
        console.print(f"[dim]Listening on http://{host}:{port}/sse[/dim]")

    run_aether_mcp(host=host, port=port, transport=transport)


@mcp_cmds.command("trust")
@click.option("--host", default="127.0.0.1", help="Transport host")
@click.option("--port", default=5002, type=int, help="SSE port")
@click.option(
    "--transport", default="sse", type=click.Choice(["sse", "stdio"]), help="Transport protocol"
)
def trust_mcp(host: str, port: int, transport: str) -> None:
    """Boot the standard CORTEX Trust MCP Server."""
    from cortex.mcp.server import run_server
    from cortex.mcp.utils import MCPServerConfig

    cfg = MCPServerConfig(host=host, port=port, transport=transport)  # type: ignore
    run_server(cfg)


@mcp_cmds.command("sovereign")
def sovereign_mcp() -> None:
    """Boot the CORTEX Sovereign MCP Server (Rust-native, Stdio)."""
    import json
    import sys

    from cortex.extensions.policy.jis_auditor import JISAuditor
    from cortex.memory.vsa import VSAPipelineBridge
    from cortex_rs import McpSovereignHost

    sys.stderr.write("🚀 Booting CORTEX Sovereign MCP Server (Rust-native, Transport: stdio)...\n")
    sys.stderr.flush()

    vsa_bridge = VSAPipelineBridge(agent_id="cortex_mcp_server")
    jis_auditor = JISAuditor(enforce_encryption=True)
    host = McpSovereignHost("cortex-sovereign-mcp", "1.0.0", vsa_bridge, jis_auditor)

    # Simple Stdio loop for MCP
    while True:
        line = sys.stdin.readline()
        if not line:
            break

        line = line.strip()
        if not line:
            continue

        try:
            response_json = host.process_request(line)  # pyright: ignore[reportAttributeAccessIssue]
            sys.stdout.write(response_json + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": None}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
