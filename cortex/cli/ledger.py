"""Immutable Ledger CLI commands for CORTEX (Wave 5)."""

import click
from rich.console import Console

from cortex.cli.common import DEFAULT_DB, _run_async, get_engine

console = Console()


@click.group(name="ledger")
def ledger_cmds():
    """Sovereign Ledger Operations (Wave 5: Immutable Merkle Trees)."""
    pass


@ledger_cmds.command("verify")
@click.option("--db", default=DEFAULT_DB, help="Database path")
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


@ledger_cmds.command("checkpoint")
@click.option("--db", default=DEFAULT_DB, help="Database path")
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


ledger_cmds_click = ledger_cmds
