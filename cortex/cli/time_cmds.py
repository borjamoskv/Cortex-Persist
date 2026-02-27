"""CLI commands: time, heartbeat."""

from __future__ import annotations

import sqlite3

import click
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli, console, get_engine, get_tracker
from cortex.cli.errors import err_empty_results, handle_cli_error

__all__ = ["time_cmd", "heartbeat_cmd"]


@cli.command("time")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--days", "-d", default=1, help="Number of days (default: 1 = today)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def time_cmd(project, days, db) -> None:
    """Show time tracking summary."""
    engine = get_engine(db)
    try:
        engine.init_db_sync()
        t = get_tracker(engine)
        if days <= 1:
            summary = t.today(project=project)
            title = "⏱ Today's Time"
        else:
            summary = t.report(project=project, days=days)
            title = f"⏱ Last {days} Days"
        if summary.total_seconds == 0:
            err_empty_results("time tracked")
            return
        _render_time_summary(summary, title)
    except (sqlite3.Error, OSError, ValueError, RuntimeError) as e:
        handle_cli_error(e, db_path=db, context="fetching time report")
    finally:
        engine.close_sync()


def _render_time_summary(summary, title: str) -> None:
    table = Table(title=title)
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")
    table.add_row("Total", summary.format_duration(summary.total_seconds))
    table.add_row("Entries", str(summary.entries))
    table.add_row("Heartbeats", str(summary.heartbeats))
    if summary.by_category:
        for cat, secs in sorted(summary.by_category.items(), key=lambda x: -x[1]):
            table.add_row(f"  {cat}", summary.format_duration(secs))
    if summary.by_project:
        table.add_row("", "")
        for proj, secs in sorted(summary.by_project.items(), key=lambda x: -x[1]):
            table.add_row(f"  📁 {proj}", summary.format_duration(secs))
    if summary.top_entities:
        table.add_row("", "")
        for entity, count in summary.top_entities[:5]:
            table.add_row(f"  📄 {entity}", f"{count} hits")
    console.print(table)


@cli.command("heartbeat")
@click.argument("project")
@click.argument("entity", default="")
@click.option("--category", "-c", default=None, help="Activity category")
@click.option("--branch", "-b", default=None, help="Git branch")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def heartbeat_cmd(project, entity, category, branch, db) -> None:
    """Record an activity heartbeat."""
    engine = get_engine(db)
    try:
        engine.init_db_sync()
        t = get_tracker(engine)
        hb_id = t.heartbeat(
            project=project,
            entity=entity,
            category=category,
            branch=branch,
        )
        t.flush()
        console.print(f"[green]✓[/] Heartbeat [bold]#{hb_id}[/] → [cyan]{project}[/]/{entity}")
    except (sqlite3.Error, OSError, ValueError, RuntimeError) as e:
        handle_cli_error(e, db_path=db, context="recording heartbeat")
    finally:
        engine.close_sync()
