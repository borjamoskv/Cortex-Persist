"""
Frontier CLI Commands
Control the R&D and Metabolism pulse of CORTEX.
"""

from __future__ import annotations

import asyncio

import click

from cortex.cli.common import console, get_engine
from cortex.extensions.daemon.frontier import FrontierDaemon


@click.group("frontier")
def frontier_cmds():
    """🚀 Frontier: Sovereign Evolution & Metabolism."""
    pass


@frontier_cmds.command("scan")
@click.option("--source", "-s", help="Specific URL or domain to ingest.")
def scan_cmd(source: str | None):
    """Scan the frontier for new intelligence (Cognitive Ingestion)."""
    console.print("[bold cyan]🚀 Starting Frontier Scan...[/bold cyan]")
    engine = get_engine()
    daemon = FrontierDaemon(engine=engine)

    if source:
        console.print(f"Ingesting source: [yellow]{source}[/yellow]")
        asyncio.run(daemon._run_ingestion())
    else:
        asyncio.run(daemon._run_ingestion())

    console.print("[bold green]✔ Ingestion cycle complete.[/bold green]")


@frontier_cmds.command("metabolize")
@click.option("--target", "-t", help="Target file or directory to metabolize.")
@click.option("--commit/--dry-run", default=False, help="Allow commits if entropy gate passes.")
def metabolize_cmd(target: str | None, commit: bool):
    """Force a metabolism cycle (Ouroboros-Omega) on target."""
    console.print("[bold magenta]♾️  Initializing Forced Metabolism Cycle...[/bold magenta]")
    engine = get_engine()
    daemon = FrontierDaemon(engine=engine, allow_commits=commit)

    asyncio.run(daemon._run_metabolism())

    mode = "COMMIT" if commit else "DRY-RUN"
    console.print(f"[bold green]✔ Metabolism cycle finished in {mode} mode.[/bold green]")
