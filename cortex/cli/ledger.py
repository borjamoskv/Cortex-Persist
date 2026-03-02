"""Immutable Ledger CLI commands for CORTEX (Wave 5)."""

import asyncio

import typer
from rich.console import Console

from cortex.cli.common import DEFAULT_DB, get_engine

ledger_cmds = typer.Typer(help="Sovereign Ledger Operations (Wave 5: Immutable Merkle Trees).")
console = Console()


@ledger_cmds.command("verify")
def verify_ledger():
    """Verify the integrity of the entire CORTEX transaction chain."""

    async def _run():
        engine = get_engine(DEFAULT_DB)
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

    asyncio.run(_run())


@ledger_cmds.command("checkpoint")
def create_checkpoint():
    """Force the creation of a Merkle Tree checkpoint."""

    async def _run():
        engine = get_engine(DEFAULT_DB)
        try:
            await engine.init_db()
            ledger = getattr(engine, "_ledger", None)
            if not ledger:
                from cortex.engine.ledger import ImmutableLedger

                ledger = ImmutableLedger(await engine.get_conn())  # type: ignore[reportArgumentType]

            root_id = await ledger.create_checkpoint_async()
            if root_id:
                console.print(
                    f"[bold green]Checkpoint created successfully.[/bold green] ID: {root_id}"
                )
            else:
                console.print("[yellow]No new transactions to checkpoint.[/yellow]")
        finally:
            await engine.close()

    asyncio.run(_run())


ledger_cmds_click = typer.main.get_command(ledger_cmds)
