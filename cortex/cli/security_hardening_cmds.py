"""CLI commands: quarantine, unquarantine, reap-ghosts."""

from __future__ import annotations

import click

from cortex.cli.common import DEFAULT_DB, _run_async, cli, console, get_engine

__all__ = ["quarantine", "unquarantine", "reap_ghosts"]


@cli.command()
@click.argument("fact_id", type=int)
@click.option("--reason", "-r", required=True, help="Why this fact is being quarantined")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def quarantine(fact_id: int, reason: str, db: str) -> None:
    """Quarantine a suspicious fact (isolate without deleting)."""
    engine = get_engine(db)
    try:
        success = _run_async(engine.quarantine(fact_id, reason))
        if success:
            console.print(
                f"[bold red]🔒 QUARANTINED[/] Fact [bold]#{fact_id}[/] — {reason}"
            )
        else:
            console.print(f"[yellow]⚠ Fact #{fact_id} not found or already quarantined[/]")
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("fact_id", type=int)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def unquarantine(fact_id: int, db: str) -> None:
    """Lift quarantine from a fact (restore to active)."""
    engine = get_engine(db)
    try:
        success = _run_async(engine.unquarantine(fact_id))
        if success:
            console.print(
                f"[bold green]🔓 RELEASED[/] Fact [bold]#{fact_id}[/] — quarantine lifted"
            )
        else:
            console.print(f"[yellow]⚠ Fact #{fact_id} not found or not quarantined[/]")
    finally:
        _run_async(engine.close())


@cli.command("reap-ghosts")
@click.option("--ttl-days", default=30, type=int, help="Ghost TTL in days (default: 30)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def reap_ghosts(ttl_days: int, db: str) -> None:
    """Reap expired ghosts (DB + Songlines)."""
    from cortex.engine.reaper import GhostReaper

    engine = get_engine(db)
    reaper = GhostReaper(ttl_days=ttl_days)

    try:

        async def _reap():
            conn = await engine.get_conn()
            return await reaper.reap_db_ghosts(conn)

        db_count = _run_async(_reap())
        sl_count = reaper.reap_songlines_ghosts()

        total = db_count + sl_count
        if total > 0:
            console.print(
                f"[bold cyan]🪦 Reaped {total} ghost(s)[/] "
                f"(DB: {db_count}, Songlines: {sl_count}, TTL: {ttl_days}d)"
            )
        else:
            console.print(f"[dim]No expired ghosts found (TTL: {ttl_days}d)[/]")
    finally:
        _run_async(engine.close())


@cli.command("bridge-audit")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def bridge_audit(db: str) -> None:
    """Audit active bridges for quarantine contamination."""
    from cortex.engine.bridge_guard import BridgeGuard

    engine = get_engine(db)
    try:

        async def _audit():
            conn = await engine.get_conn()
            return await BridgeGuard.audit_bridges(conn)

        results = _run_async(_audit())

        if not results:
            console.print("[dim]No active bridges found[/]")
            return

        from rich.table import Table

        table = Table(title="🌉 Bridge Audit", show_lines=True)
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Project", style="white")
        table.add_column("Source", style="blue")
        table.add_column("Q-Ratio", style="yellow", justify="right")
        table.add_column("Status", style="bold")

        for r in results:
            status = "[green]✅ CLEAN[/]" if r["allowed"] else f"[red]🚫 BLOCKED[/] {r['reason']}"
            table.add_row(
                str(r["fact_id"]),
                r["project"],
                r["source_project"] or "[dim]unknown[/]",
                f"{r['quarantine_ratio']:.1%}",
                status,
            )

        console.print(table)
    finally:
        _run_async(engine.close())
