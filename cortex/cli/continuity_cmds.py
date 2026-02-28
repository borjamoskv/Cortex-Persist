"""CORTEX CLI — Continuity commands.

Commands for querying and managing the cognitive continuity system.

    cortex continuity briefing    Show the current briefing
    cortex continuity timeline    Show recent timeline events
    cortex continuity check       Run a manual continuity scan
    cortex continuity status      Show continuity system health
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group("continuity")
def continuity_cmds() -> None:
    """🧠 Cognitive Continuity System — persistent clock across AI invocations."""


@continuity_cmds.command("briefing")
@click.option("--hours", "-h", default=8.0, help="Briefing window in hours")
@click.option("--raw", is_flag=True, help="Output raw markdown without Rich formatting")
def briefing(hours: float, raw: bool) -> None:
    """Show the current cognitive continuity briefing."""
    from cortex.daemon.monitors.continuity import ContinuityMonitor

    text = ContinuityMonitor.get_briefing()
    if raw:
        click.echo(text)
    else:
        console.print(Panel(Markdown(text), title="🧠 Continuity Briefing", border_style="cyan"))


@continuity_cmds.command("timeline")
@click.option("--hours", "-h", default=8.0, help="Hours to look back")
@click.option("--type", "-t", "event_type", default=None, help="Filter by event type")
@click.option("--json-out", is_flag=True, help="Output as JSON")
def timeline(hours: float, event_type: str | None, json_out: bool) -> None:
    """Show recent timeline events."""
    from cortex.daemon.monitors.continuity import ContinuityMonitor

    events = ContinuityMonitor.get_timeline(hours=hours)

    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]

    if json_out:
        click.echo(json.dumps(events, indent=2, ensure_ascii=False))
        return

    if not events:
        console.print("[dim]No events in the last {:.0f} hours.[/dim]".format(hours))
        return

    table = Table(title=f"⏳ Timeline — Last {hours:.0f}h ({len(events)} events)")
    table.add_column("Time", style="cyan", width=16)
    table.add_column("Type", style="magenta", width=16)
    table.add_column("Project", style="green", width=14)
    table.add_column("Summary", style="white")
    table.add_column("⭐", justify="center", width=3)

    type_icons = {
        "git_commit": "📦",
        "git_baseline": "🆕",
        "fact_created": "🧠",
        "process_started": "🟢",
        "process_stopped": "🔴",
        "file_activity": "📝",
    }

    for ev in events:
        ts = ev.get("timestamp", "")[:16]
        et = ev.get("event_type", "?")
        icon = type_icons.get(et, "·")
        importance = ev.get("importance", 1)
        stars = "★" * importance

        table.add_row(
            ts,
            f"{icon} {et}",
            ev.get("project", "—"),
            ev.get("summary", ""),
            stars,
        )

    console.print(table)


@continuity_cmds.command("check")
def check_cmd() -> None:
    """Run a manual continuity scan now."""
    from cortex.daemon.monitors.continuity import ContinuityMonitor

    monitor = ContinuityMonitor()
    console.print("[bold cyan]⏳ Running continuity scan...[/bold cyan]")

    start = time.monotonic()
    alerts = monitor.check()
    duration_ms = (time.monotonic() - start) * 1000

    if alerts:
        for alert in alerts:
            console.print(f"[yellow]⚠️ {alert.issue}:[/yellow] {alert.detail}")
    else:
        console.print("[green]✅ Continuity intact — no gaps detected[/green]")

    console.print(f"[dim]Scan completed in {duration_ms:.0f}ms[/dim]")
    console.print("[dim]Briefing regenerated at ~/.cortex/continuity/briefing.md[/dim]")


@continuity_cmds.command("status")
def status_cmd() -> None:
    """Show continuity system health."""
    from pathlib import Path

    from cortex.daemon.monitors.continuity import (
        BRIEFING_FILE,
        CONTINUITY_DIR,
        STATE_FILE,
        TIMELINE_FILE,
    )

    table = Table(title="🧠 Continuity System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Detail", style="dim")

    # Timeline file
    if TIMELINE_FILE.exists():
        size_kb = TIMELINE_FILE.stat().st_size / 1024
        with open(TIMELINE_FILE) as f:
            line_count = sum(1 for _ in f)
        table.add_row(
            "Timeline",
            f"✅ {line_count} events",
            f"{size_kb:.1f} KB",
        )
    else:
        table.add_row("Timeline", "❌ Missing", "Run `cortex continuity check`")

    # Briefing file
    if BRIEFING_FILE.exists():
        mtime = datetime.fromtimestamp(BRIEFING_FILE.stat().st_mtime, tz=timezone.utc)
        age_min = (time.time() - BRIEFING_FILE.stat().st_mtime) / 60
        table.add_row(
            "Briefing",
            f"✅ Fresh ({age_min:.0f}m ago)",
            mtime.strftime("%H:%M UTC"),
        )
    else:
        table.add_row("Briefing", "❌ Missing", "Run `cortex continuity check`")

    # State file
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        repos = len(state.get("last_git_hashes", {}))
        facts = state.get("last_fact_count", 0)
        last_epoch = state.get("last_check_epoch", 0)
        if last_epoch > 0:
            age_min = (time.time() - last_epoch) / 60
            table.add_row(
                "State",
                f"✅ {repos} repos tracked",
                f"Last check: {age_min:.0f}m ago, {facts} facts",
            )
        else:
            table.add_row("State", "⚠️ No checks yet", "")
    else:
        table.add_row("State", "❌ Missing", "")

    console.print(table)
