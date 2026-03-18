"""CLI commands for Swarm Coexistence Event (Jornadas)."""

import asyncio

import click
from rich.console import Console
from rich.table import Table

from cortex.cli.common import coro
from cortex.extensions.swarm.manager import get_swarm_manager

console = Console()


@click.group()
def jornadas() -> None:
    """Manage Swarm Coexistence Events (Jornadas)."""
    pass


@jornadas.command("trigger")
@click.option("--dry-run", is_flag=True, help="Run the protocol without modifying the database.")
@coro
async def trigger(dry_run: bool) -> None:
    """Trigger a global synchronization event for the Swarm."""
    manager = get_swarm_manager()
    
    # Normally the SwarmManager is set up by the engine, but for ad-hoc CLI triggers,
    # we may need to initialize it if it isn't fully set up.
    if not manager._initialized or not manager.jornadas:
        from cortex.engine.core import get_cortex
        from cortex.engine.embeddings import CortexEmbeddingEncoder
        # Need an active cortex instance for DB connection and encoder
        try:
            ctx = await get_cortex()
            encoder = CortexEmbeddingEncoder(ctx.model_id) if hasattr(ctx, "model_id") else None
            manager.setup_jornadas(db_conn=ctx, encoder=encoder)
        except Exception as e:
            console.print(f"[red]Error initializing CORTEX for Jornadas: {e}[/red]")
            return

    console.print("[cyan]🏔️ Initiating Swarm Coexistence Event (Jornada)...[/cyan]")
    if dry_run:
        console.print("[yellow]Dry run mode enabled. No data will be modified.[/yellow]")
        
    try:
        report = await manager.trigger_jornada(dry_run=dry_run)
        
        console.print(f"\\n[bold green]Jornada {report.jornada_id} Completed![/bold green]")
        
        table = Table(show_header=False, box=None)
        table.add_row("Duration:", f"{report.duration_s:.2f}s")
        table.add_row("Nodes Participated:", str(report.nodes_participated))
        table.add_row("Global Exergy:", f"{report.swarm_exergy_efficiency:.3f}")
        
        if report.consolidation:
            cons = report.consolidation
            table.add_row("Crystals Purged:", str(cons.purged))
            table.add_row("Crystals Merged:", str(cons.merged))
            table.add_row("Axioms Promoted:", str(cons.promoted))
            table.add_row("Total Scanned:", str(cons.total_scanned))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Jornada failed: {e}[/red]")
