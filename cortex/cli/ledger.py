"""Sovereign Ledger CLI commands for CORTEX (Waves 5 & 6)."""

import click
from rich.console import Console

from cortex.cli.common import DEFAULT_DB
from cortex.ledger.store import LedgerStore
from cortex.ledger.verifier import LedgerVerifier

console = Console()


@click.group(name="ledger")
def ledger_cmds():
    """Sovereign Ledger Operations (Wave 6: High-Performance Chaining)."""
    pass


@ledger_cmds.command("verify")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--full", is_flag=True, help="Perform full cryptographic verify")
def verify_ledger(db: str, full: bool):
    """Verify hash chain integrity."""
    store = LedgerStore(db)
    verifier = LedgerVerifier(store)

    with console.status("[bold cyan]Verifying ledger integrity..."):
        result = verifier.verify_chain()

    if result["valid"]:
        console.print(
            f"[bold green]Ledger is VALID[/bold green] ({result['checked_events']} events checked)"
        )
        stats = result.get("enrichment_stats", {})
        console.print(
            f"Enrichment: [green]Indexed: {stats.get('indexed', 0)}[/green] | "
            f"[yellow]Pending: {stats.get('pending', 0)}[/yellow] | "
            f"[red]Failed: {stats.get('failed', 0)}[/red]"
        )
    else:
        violations = result["violations"]
        console.print(f"[bold red]Ledger is COMPROMISED[/bold red]: {len(violations)} violations")
        for v in violations[:10]:
            console.print(f"  - {v}")


@ledger_cmds.command("checkpoint")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--batch", default=10, help="Events per checkpoint")
def create_checkpoint(db: str, batch: int):
    """Compute and store a Merkle root for uncheckpointed events."""
    store = LedgerStore(db)
    verifier = LedgerVerifier(store)

    with console.status("[bold cyan]Creating Merkle checkpoint..."):
        root_id = verifier.create_checkpoint(batch_size=batch)

    if root_id:
        console.print(f"[bold green]Checkpoint created successfully.[/bold green] ID: {root_id}")
    else:
        console.print(
            "[yellow]No new events available for checkpointing "
            "(batch size not reached).[/yellow]"
        )


ledger_cmds_click = ledger_cmds
