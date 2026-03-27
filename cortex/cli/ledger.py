"""Immutable Ledger CLI commands for CORTEX (Wave 5)."""

import click
from rich.console import Console
from rich.panel import Panel

from cortex.cli.common import DEFAULT_DB, _run_async, get_engine, get_tracker

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
                    f"[bold green]Ledger is VALID[/bold green] "
                    f"({result.get('tx_checked')} TXs, {result.get('roots_checked')} Roots)"
                )
            else:
                console.print(
                    f"[bold red]Ledger is COMPROMISED[/bold red]: "
                    f"{len(result.get('violations', []))} violations"
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
            ledger_inst = engine.ledger

            if not ledger_inst:
                console.print("[bold red]Error:[/] Ledger not available in engine.")
                return

            root_id = await ledger_inst.create_checkpoint()
            if root_id:
                console.print(
                    f"[bold green]Checkpoint created successfully.[/bold green] ID: {root_id}"
                )
            else:
                console.print("[yellow]No new transactions to checkpoint.[/yellow]")
        finally:
            await engine.close()

    _run_async(_run())


@ledger_cmds.command(name="list")
@click.option("--project", default="", help="Filter by project")
@click.option("--limit", default=20, help="Max entries to show")
@click.option("--days", default=7, help="Show last N days")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def list_ledger_cmd(project: str, limit: int, days: int, db: str):
    """List ledger entries (unified view)."""

    async def _run():
        engine = get_engine(db)
        try:
            await engine.init_db()
            tracker = await get_tracker(engine)
            report = await tracker.report(project=project, days=days)

            if not report.entries and not report.heartbeats:
                console.print("[yellow]No entries found for the selected period.[/]")
                return

            console.print(Panel(
                f"[bold blue]Ledger Summary[/]\n"
                f"Project: {project or 'ALL'}\n"
                f"Last {days} days: {report.total_seconds / 3600:.1f}h total\n"
                f"Entries: {report.entries} | Heartbeats: {report.heartbeats}",
                title="CORTEX"
            ))
        finally:
            await engine.close()

    _run_async(_run())


@ledger_cmds.command("record")
@click.option("--project", required=True, help="Project identifier.")
@click.option("--action", required=True, help="Action name.")
@click.option("--detail", required=True, help="JSON-formatted detail.")
@click.option("--db", default=DEFAULT_DB, help="Database path.")
def record_transaction(project, action, detail, db):
    """Record a manual transaction in the ledger."""
    import json

    async def _run():
        engine = get_engine(db)
        try:
            await engine.init_db()
            det = json.loads(detail)

            ledger_inst = engine.ledger
            if not ledger_inst:
                console.print("[bold red]Error:[/] Ledger not available in engine.")
                return

            h = await ledger_inst.record_transaction(project, action, det)
            console.print(f"[bold green]Transaction recorded.[/] Hash: [dim]{h}[/]")
        except json.JSONDecodeError:
            console.print("[bold red]Error:[/] 'detail' must be a valid JSON string.")
        finally:
            await engine.close()

    _run_async(_run())


ledger_cmds_click = ledger_cmds
