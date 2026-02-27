"""CLI commands: handoff generate, handoff load."""

from __future__ import annotations

import asyncio
import json
import sqlite3

import click
from rich.panel import Panel
from rich.table import Table

from cortex.agents.handoff import generate_handoff, load_handoff, save_handoff
from cortex.cli.common import DEFAULT_DB, cli, console, get_engine
from cortex.cli.errors import err_empty_results, handle_cli_error

__all__ = ["handoff", "generate", "load"]


def _run_async(coro):
    """Helper to run async coroutines from sync CLI."""
    return asyncio.run(coro)


@cli.group()
def handoff() -> None:
    """Session Handoff Protocol — compact session continuity."""
    pass


@handoff.command("generate")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--pending", "-p", multiple=True, help="Pending work items (repeat for multiple)")
@click.option(
    "--mood", "-m", default="neutral", help="Session mood (e.g. productive, blocked, exploring)"
)
@click.option("--focus", "-f", multiple=True, help="Focus projects (repeat for multiple)")
@click.option("--out", default=None, help="Output path (default: ~/.cortex/handoff.json)")
def generate(db, pending, mood, focus, out) -> None:
    """Generate a session handoff from current CORTEX state."""
    from pathlib import Path

    engine = get_engine(db)
    try:
        session_meta = {
            "focus_projects": list(focus),
            "pending_work": list(pending),
            "mood": mood,
        }

        with console.status("[bold blue]Generating handoff...[/]"):
            data = _run_async(generate_handoff(engine, session_meta=session_meta))

        out_path = Path(out) if out else None
        saved_path = save_handoff(data, path=out_path)

        # Display summary
        console.print(
            Panel(
                f"[bold green]✓ Handoff generated[/]\n"
                f"Decisions: {len(data['hot_decisions'])} | "
                f"Ghosts: {len(data['active_ghosts'])} | "
                f"Errors: {len(data['recent_errors'])} | "
                f"Active projects: {len(data['active_projects'])}\n"
                f"Saved to: {saved_path}",
                title="🤝 Session Handoff",
                border_style="cyan",
            )
        )
    except (sqlite3.Error, OSError, ValueError, RuntimeError, KeyError) as e:
        handle_cli_error(e, db_path=db, context="generating handoff")
    finally:
        _run_async(engine.close())


@handoff.command("load")
@click.option("--path", default=None, help="Path to handoff.json")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def load(path, json_output) -> None:
    """Load and display the current session handoff."""
    from pathlib import Path as P

    target = P(path) if path else None
    data = load_handoff(path=target)

    if data is None:
        err_empty_results("handoff", suggestion="Run 'cortex handoff generate' first.")
        return

    if json_output:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    _display_handoff_summary(data)
    _display_pending_work(data)
    _display_section_table(
        data, "hot_decisions", "\n🔥 Hot Decisions", "content", "Decision", "cyan"
    )
    _display_section_table(
        data, "active_ghosts", "\n👻 Active Ghosts", "reference", "Reference", "cyan"
    )
    _display_section_table(data, "recent_errors", "\n🔴 Recent Errors", "content", "Error", "red")

    active = data.get("active_projects", [])
    if active:
        console.print(f"\n[bold green]📂 Active Projects (24h):[/] {', '.join(active)}")


def _truncate(text: str, max_len: int = 70) -> str:
    """Truncate text with ellipsis if it exceeds max_len."""
    return text[:max_len] + "..." if len(text) > max_len else text


def _display_handoff_summary(data: dict) -> None:
    """Display the handoff header panel."""
    session = data.get("session", {})
    stats = data.get("stats", {})
    console.print(
        Panel(
            f"[dim]Generated:[/] {data.get('generated_at', '?')}\n"
            f"[dim]Mood:[/] {session.get('mood', '?')} | "
            f"[dim]Focus:[/] {', '.join(session.get('focus_projects', [])) or 'none'}\n"
            f"[dim]Facts:[/] {stats.get('total_facts', 0)} | "
            f"[dim]Projects:[/] {stats.get('total_projects', 0)} | "
            f"[dim]DB:[/] {stats.get('db_size_mb', 0)} MB",
            title="🤝 Session Handoff",
            border_style="cyan",
        )
    )


def _display_pending_work(data: dict) -> None:
    """Display pending work items."""
    pending = data.get("session", {}).get("pending_work", [])
    if pending:
        console.print("\n[bold yellow]⏳ Pending Work[/]")
        for item in pending:
            console.print(f"  • {item}")


def _display_section_table(
    data: dict,
    key: str,
    title: str,
    content_field: str,
    column_name: str,
    project_style: str,
) -> None:
    """Display a section of handoff data as a Rich table."""
    items = data.get(key, [])
    if not items:
        return
    table = Table(title=title)
    table.add_column("#", style="dim", width=4)
    table.add_column("Project", style=project_style, width=15)
    table.add_column(column_name, width=55)
    for item in items:
        text = _truncate(item[content_field])
        table.add_row(str(item["id"]), item["project"], text)
    console.print(table)
