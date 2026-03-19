"""
CORTEX v6 — Audit Commands
Commands for system security and architectural auditing.
"""

import asyncio

import click

from cortex.audit.frontier import FrontierAuditor
from cortex.cli.common import console, get_engine


@click.group("audit")
def audit_cmds():
    """🛡️ Sovereign Audit: Security & Entropy detection."""
    pass


@audit_cmds.command("frontier")
@click.option(
    "--project", "-p",
    required=True,
    help="Target project name to evaluate.",
)
@click.option(
    "--model", "-m",
    help="Override default provider (e.g. openai, anthropic).",
)
@click.option(
    "--timeout", "-t",
    default=120.0,
    type=float,
    help="Timeout per agent in seconds (default: 120).",
)
@click.option(
    "--no-persist",
    is_flag=True,
    default=False,
    help="Skip writing audit report to the database.",
)
def frontier_cmd(
    project: str,
    model: str | None,
    timeout: float,
    no_persist: bool,
):
    """Execute a lethal cognitive audit using the triad."""
    console.print(
        f"[bold magenta]🐺 Awakening Frontier Auditor "
        f"for project: {project}...[/bold magenta]"
    )

    engine = get_engine()
    auditor = FrontierAuditor(
        engine=engine,
        model_override=model,
        timeout=timeout,
        persist=not no_persist,
    )

    with console.status(
        "[cyan]Triad is dissecting local definitions...[/cyan]"
    ):
        result = asyncio.run(auditor.run_audit(project))

    if result["status"] == "SUCCESS":
        console.print(
            f"[bold green]✔ Audit executed via "
            f"{result['provider']} "
            f"({result['latency']:.0f}ms)[/bold green]"
        )
        console.print("\n[bold]⚖️ FRONTIER REPORT:[/bold]")
        console.print(result["report_markdown"])
    else:
        console.print(
            f"[bold red]❌ Audit degraded — "
            f"{result['provider']}[/bold red]"
        )
        console.print(result["report_markdown"])

    # Show error chain if any
    errors = result.get("errors", [])
    if errors:
        console.print("\n[dim]─── Fallback Chain ───[/dim]")
        for err in errors:
            console.print(f"  [dim]· {err}[/dim]")
