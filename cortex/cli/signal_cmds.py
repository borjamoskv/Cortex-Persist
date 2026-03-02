# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CLI commands: cortex signal emit/poll/history/stats.

The nervous system of MOSKV-1 — exposed through the command line.
"""

from __future__ import annotations

import json
import sqlite3

import click
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli, console

__all__: list[str] = []


def _get_signal_bus(db: str):
    """Create a SignalBus instance from a database path."""
    from cortex.signals.bus import SignalBus

    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL")
    return SignalBus(conn), conn


@cli.group("signal")
def signal_cmds() -> None:
    """Signal Bus — L1 consciousness for cross-tool communication."""
    pass


@signal_cmds.command("emit")
@click.argument("event_type")
@click.argument("payload_json", default="{}")
@click.option("--source", "-s", default="cli", help="Emitter identity")
@click.option("--project", "-p", default=None, help="Project scope")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def emit_cmd(event_type: str, payload_json: str, source: str, project: str | None, db: str) -> None:
    """Emit a signal into the bus.

    Examples:

        cortex signal emit plan:done '{"files": ["main.py"]}'

        cortex signal emit error:critical '{"trace": "..."}' -s arkitetv-1
    """
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        console.print(f"[red]✗ Invalid JSON payload:[/] {payload_json}")
        raise SystemExit(1) from None

    bus, conn = _get_signal_bus(db)
    try:
        signal_id = bus.emit(event_type, payload, source=source, project=project)
        console.print(
            f"[green]⚡[/] Signal emitted: [bold cyan]{event_type}[/] "
            f"(#{signal_id}) from [dim]{source}[/]"
        )
    finally:
        conn.close()


@signal_cmds.command("poll")
@click.option("--type", "event_type", default=None, help="Filter by event type")
@click.option("--source", "-s", default=None, help="Filter by emitter")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--consumer", "-c", default="cli", help="Consumer identity")
@click.option("--limit", "-n", default=20, help="Max signals")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def poll_cmd(
    event_type: str | None,
    source: str | None,
    project: str | None,
    consumer: str,
    limit: int,
    db: str,
) -> None:
    """Poll and consume unconsumed signals.

    Consumed signals will not appear in subsequent polls by the same consumer.
    """
    bus, conn = _get_signal_bus(db)
    try:
        signals = bus.poll(
            event_type=event_type,
            source=source,
            project=project,
            consumer=consumer,
            limit=limit,
        )
        if not signals:
            console.print("[dim]No unconsumed signals matching filter.[/]")
            return

        table = Table(
            title=f"⚡ Consumed Signals ({len(signals)})",
            border_style="bright_green",
        )
        table.add_column("ID", style="bold", width=5)
        table.add_column("Type", style="cyan", width=20)
        table.add_column("Source", style="dim", width=16)
        table.add_column("Project", width=14)
        table.add_column("Payload", width=40)
        table.add_column("Time", style="dim", width=19)

        for sig in signals:
            payload_str = json.dumps(sig.payload)
            if len(payload_str) > 37:
                payload_str = payload_str[:37] + "..."
            table.add_row(
                str(sig.id),
                sig.event_type,
                sig.source,
                sig.project or "—",
                payload_str,
                str(sig.created_at)[:19],
            )
        console.print(table)
    finally:
        conn.close()


@signal_cmds.command("history")
@click.option("--type", "event_type", default=None, help="Filter by event type")
@click.option("--source", "-s", default=None, help="Filter by emitter")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--limit", "-n", default=20, help="Max signals")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def history_cmd(
    event_type: str | None,
    source: str | None,
    project: str | None,
    limit: int,
    db: str,
) -> None:
    """Show signal history (including consumed)."""
    bus, conn = _get_signal_bus(db)
    try:
        signals = bus.history(
            event_type=event_type,
            source=source,
            project=project,
            limit=limit,
        )
        if not signals:
            console.print("[dim]No signals in history.[/]")
            return

        table = Table(
            title=f"📡 Signal History ({len(signals)})",
            border_style="cyan",
        )
        table.add_column("ID", style="bold", width=5)
        table.add_column("Type", style="cyan", width=20)
        table.add_column("Source", style="dim", width=16)
        table.add_column("Project", width=14)
        table.add_column("Consumed", width=10)
        table.add_column("Payload", width=35)
        table.add_column("Time", style="dim", width=19)

        for sig in signals:
            payload_str = json.dumps(sig.payload)
            if len(payload_str) > 32:
                payload_str = payload_str[:32] + "..."
            consumed = f"[green]✓ {len(sig.consumed_by)}[/]" if sig.consumed_by else "[dim]—[/]"
            table.add_row(
                str(sig.id),
                sig.event_type,
                sig.source,
                sig.project or "—",
                consumed,
                payload_str,
                str(sig.created_at)[:19],
            )
        console.print(table)
    finally:
        conn.close()


@signal_cmds.command("stats")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def stats_cmd(db: str) -> None:
    """Show signal bus statistics."""
    bus, conn = _get_signal_bus(db)
    try:
        s = bus.stats()
        console.print()
        console.print("[bold cyan]📊 Signal Bus Stats[/]")
        console.print(f"  Total signals:    [bold]{s['total']}[/]")
        console.print(f"  Unconsumed:       [bold yellow]{s['unconsumed']}[/]")
        console.print()

        if s["by_type"]:
            console.print("  [dim]By type:[/]")
            for t, c in s["by_type"].items():
                console.print(f"    [cyan]{t}[/]: {c}")

        if s["by_source"]:
            console.print("  [dim]By source:[/]")
            for src, c in s["by_source"].items():
                console.print(f"    [dim]{src}[/]: {c}")
        console.print()
    finally:
        conn.close()


@signal_cmds.command("gc")
@click.option("--days", default=30, help="Max age for consumed signals")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def gc_cmd(days: int, db: str) -> None:
    """Garbage collect old consumed signals."""
    bus, conn = _get_signal_bus(db)
    try:
        pruned = bus.gc(max_age_days=days)
        console.print(
            f"[green]🗑️[/] Pruned [bold]{pruned}[/] consumed signal(s) older than {days} days."
        )
    finally:
        conn.close()
