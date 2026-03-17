"""
CORTEX v6 — Audit Commands
Commands for system security and architectural auditing.
"""

from __future__ import annotations

import asyncio

import click

from cortex.audit.frontier import FrontierAuditor
from cortex.cli.common import console, get_engine


@click.group("audit")
def audit_cmds():
    """🛡️ Sovereign Audit: Security & Entropy detection."""
    pass


@audit_cmds.command("frontier")
@click.option("--project", "-p", required=True, help="Target project name to evaluate.")
@click.option(
    "--model", "-m", help="Override default SovereignLLM with a specific preferred provider."
)
def frontier_cmd(project: str, model: str | None):
    """Execute a lethal cognitive audit using the TOM, OLIVER & BENJI triad."""
    console.print(
        f"[bold magenta]🐺 Awakening Frontier Auditor for project: {project}...[/bold magenta]"
    )

    engine = get_engine()
    auditor = FrontierAuditor(engine=engine, model_override=model)

    # Run standard Sovereign context
    with console.status("[cyan]Triad is dissecting local definitions...[/cyan]"):
        result = asyncio.run(auditor.run_audit(project))

    if result["status"] == "SUCCESS":
        console.print(
            f"[bold green]✔ Audit executed via {result['provider']} "
            f"({result['latency']:.0f}ms)[/bold green]"
        )
        console.print("\n[bold]⚖️ FRONTIER REPORT:[/bold]")
        console.print(result["report_markdown"])
    else:
        # Fallback or complete failure
        console.print(
            f"[bold red]❌ Critical failure during audit generation "
            f"({result['provider']})[/bold red]"
        )
        console.print(result["report_markdown"])
