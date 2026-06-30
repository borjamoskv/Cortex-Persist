# [C5-REAL] Exergy-Maximized
"""Experimental Thermodynamic Apoptosis Command."""

from __future__ import annotations

import asyncio
import os
import click
from rich.panel import Panel
from rich.text import Text

from babylon60.cli.common import _run_async, cli, console
from babylon60.engine.causal.ledger_apoptosis import ThermodynamicLedgerApoptosis
from babylon60.memory.apoptosis import ApoptosisAgent


async def _execute_apoptosis(target: str, tenant: str) -> None:
    text = Text(f"Apoptosis triggered on target: {target}", style="bold red")
    panel = Panel(text, title="[blink]THERMODYNAMIC APOPTOSIS[/blink]", border_style="red")
    console.print(panel)

    if not os.path.exists(target):
        console.print(f"[bold red]Error: Target path '{target}' does not exist.[/bold red]")
        return

    with console.status(
        f"[bold red]Executing cell death (entropy pruning) on {target}...[/bold red]", spinner="bouncingBar"
    ):
        # Determine target type
        if target.endswith(".aof"):
            console.print("[yellow]Detected Append-Only File (AOF). Triggering Thermodynamic Ledger Apoptosis...[/yellow]")
            apoptosis = ThermodynamicLedgerApoptosis(target)
            retained = apoptosis.trigger_snapshot()
            console.print(f"[bold green]AOF Apoptosis complete. Bounded snapshot generated. Retained {retained} active nodes.[/bold green]")
        
        elif target.endswith(".db"):
            console.print(f"[yellow]Detected SQLite database. Running ApoptosisAgent for tenant '{tenant}'...[/yellow]")
            # Initialize with default free tier limits
            agent = ApoptosisAgent(db_path=target, atp_free_threshold=0.4, max_free_facts=1000)
            stats = await agent.run_apoptosis_cycle(tenant_id=tenant)
            console.print(
                f"[bold green]Database Apoptosis complete.\n"
                f"  Scanned: {stats['scanned']}\n"
                f"  Tombstoned: {stats['tombstoned']}\n"
                f"  Errors: {len(stats['errors'])}[/bold green]"
            )
            if stats["errors"]:
                console.print(f"[bold red]Errors encountered: {stats['errors']}[/bold red]")
        
        else:
            console.print(f"[bold red]Error: Target '{target}' is not a recognized .aof or .db file.[/bold red]")


@cli.command("apoptosis")
@click.argument("target")
@click.option("--tenant", default="default", help="Tenant ID to target for SQLite database prune.")
def apoptosis_cmd(target: str, tenant: str) -> None:
    """Trigger thermodynamic apoptosis on a target (.aof or .db)."""
    _run_async(_execute_apoptosis(target, tenant))
