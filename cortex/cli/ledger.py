<<<<<<< HEAD
"""Sovereign Ledger CLI commands for CORTEX (Waves 5 & 6)."""
=======
"""Immutable Ledger CLI commands for CORTEX (Wave 5)."""
>>>>>>> origin/main

import click
from rich.console import Console

<<<<<<< HEAD
from cortex.cli.common import DEFAULT_DB
from cortex.ledger.store import LedgerStore
from cortex.ledger.verifier import LedgerVerifier
=======
from cortex.cli.common import DEFAULT_DB, _run_async, get_engine
>>>>>>> origin/main

console = Console()


@click.group(name="ledger")
def ledger_cmds():
<<<<<<< HEAD
    """Sovereign Ledger Operations (Wave 6: High-Performance Chaining)."""
=======
    """Sovereign Ledger Operations (Wave 5: Immutable Merkle Trees)."""
>>>>>>> origin/main
    pass


@ledger_cmds.command("verify")
@click.option("--db", default=DEFAULT_DB, help="Database path")
<<<<<<< HEAD
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
=======
def verify_ledger(db):
    """Verify the integrity of the entire CORTEX transaction chain."""

    async def _run():
        engine = get_engine(db)
        try:
            await engine.init_db()
            result = await engine.verify_ledger()
            if result.get("valid"):
                console.print(
                    f"[bold green]Ledger is VALID[/bold green] ({result.get('tx_checked')} TXs, {result.get('roots_checked')} Roots)"
                )
            else:
                console.print(
                    f"[bold red]Ledger is COMPROMISED[/bold red]: {len(result.get('violations', []))} violations"
                )
                for v in result.get("violations", [])[:5]:
                    console.print(f"  - {v}")
        finally:
            await engine.close()

    _run_async(_run())
>>>>>>> origin/main


@ledger_cmds.command("checkpoint")
@click.option("--db", default=DEFAULT_DB, help="Database path")
<<<<<<< HEAD
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
            "[yellow]No new events available for checkpointing (batch size not reached).[/yellow]"
        )
=======
def create_checkpoint(db):
    """Force the creation of a Merkle Tree checkpoint."""

    async def _run():
        engine = get_engine(db)
        try:
            await engine.init_db()
            ledger_inst = getattr(engine, "_ledger", None)
            if not ledger_inst:
                from cortex.engine.ledger import ImmutableLedger

                # Re-using the connection from the engine
                conn = await engine.get_conn()
                ledger_inst = ImmutableLedger(conn)  # type: ignore[reportArgumentType]

            root_id = await ledger_inst.create_checkpoint_async()
            if root_id:
                console.print(
                    f"[bold green]Checkpoint created successfully.[/bold green] ID: {root_id}"
                )
            else:
                console.print("[yellow]No new transactions to checkpoint.[/yellow]")
        finally:
            await engine.close()

    _run_async(_run())
>>>>>>> origin/main


ledger_cmds_click = ledger_cmds
