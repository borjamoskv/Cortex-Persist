"""CORTEX CLI — Session management commands.

Commands:
    cortex session start "<task>"  — Launch autonomous agent session
    cortex session list            — List all sessions
    cortex session status <id>     — Detailed session view
    cortex session cancel <id>     — Cancel running session
    cortex session logs <id>       — Show session execution logs
"""

from __future__ import annotations

import asyncio
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _get_store():
    """Lazy-load SessionStore to avoid import-time DB access."""
    from cortex.agents.session import SessionStore

    return SessionStore()


@click.group("session")
def session_cmds():
    """Autonomous agent session management."""


@session_cmds.command("start")
@click.argument("task")
@click.option(
    "--workdir",
    default=None,
    help="Working directory for the session (default: cwd).",
)
def session_start(task: str, workdir: str | None) -> None:
    """Launch an autonomous agent session with a high-level task."""
    import os

    from cortex.agents.agent_tools import register_builtin_tools
    from cortex.agents.executor import AutonomousExecutor
    from cortex.agents.session import SessionStore
    from cortex.agents.tools import ToolRegistry

    store = SessionStore()
    session = store.create(task)
    wdir = workdir or os.getcwd()

    console.print(
        Panel(
            f"[bold cyan]Session ID:[/bold cyan] {session.session_id}\n"
            f"[bold]Task:[/bold] {task}\n"
            f"[bold]Workdir:[/bold] {wdir}\n"
            f"[bold]Status:[/bold] {session.status.value}",
            title="[bold]🤖 Autonomous Session Created[/bold]",
            border_style="cyan",
        )
    )

    # Build tool registry
    tools = ToolRegistry()
    register_builtin_tools(tools, workdir=wdir)

    # Run executor
    executor = AutonomousExecutor(session, store, tools)

    console.print("[dim]Executing plan → execute → verify lifecycle...[/dim]\n")

    try:
        result = asyncio.run(executor.run())
    except KeyboardInterrupt:
        store.cancel(session.session_id)
        console.print("\n[yellow]⚠ Session cancelled by user[/yellow]")
        sys.exit(1)

    # Show result
    status_color = {
        "completed": "green",
        "failed": "red",
        "cancelled": "yellow",
    }.get(result.status.value, "white")

    console.print(
        Panel(
            f"[bold]Status:[/bold] [{status_color}]{result.status.value.upper()}[/{status_color}]\n"
            f"[bold]Steps:[/bold] {result.completed_steps}/{result.total_steps}\n"
            f"[bold]Duration:[/bold] {result.duration_s}s\n"
            f"[bold]Files modified:[/bold] {len(result.files_modified)}",
            title=f"[bold]Session {result.session_id[:8]}[/bold]",
            border_style=status_color,
        )
    )

    if result.error:
        console.print(f"\n[red]Error: {result.error}[/red]")

    if result.status.value == "failed":
        sys.exit(1)


@session_cmds.command("list")
@click.option(
    "--status",
    "-s",
    default=None,
    type=click.Choice(
        ["planning", "executing", "verifying", "completed", "failed", "cancelled"],
        case_sensitive=False,
    ),
    help="Filter by status.",
)
@click.option("--limit", "-n", default=20, help="Max sessions to show.")
def session_list(status: str | None, limit: int) -> None:
    """List all autonomous sessions."""
    from cortex.agents.session import SessionStatus

    store = _get_store()

    filter_status = SessionStatus(status) if status else None
    sessions = store.list_sessions(status=filter_status, limit=limit)

    if not sessions:
        console.print("[dim]No sessions found.[/dim]")
        return

    table = Table(
        title="Agent Sessions",
        show_lines=True,
        title_style="bold cyan",
    )
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Status", width=12)
    table.add_column("Task", max_width=50)
    table.add_column("Steps", justify="right", width=8)
    table.add_column("Duration", justify="right", width=10)

    status_styles = {
        "planning": "blue",
        "executing": "yellow",
        "verifying": "magenta",
        "completed": "green",
        "failed": "red",
        "cancelled": "dim",
    }

    for s in sessions:
        style = status_styles.get(s.status.value, "white")
        table.add_row(
            s.session_id[:8],
            f"[{style}]{s.status.value}[/{style}]",
            s.task[:50],
            f"{s.completed_steps}/{s.total_steps}",
            f"{s.duration_s}s",
        )

    console.print(table)


@session_cmds.command("status")
@click.argument("session_id")
def session_status(session_id: str) -> None:
    """Show detailed status of a session."""
    store = _get_store()
    session = store.get(session_id)

    if session is None:
        console.print(f"[red]Session not found: {session_id}[/red]")
        sys.exit(1)

    status_colors = {
        "planning": "blue",
        "executing": "yellow",
        "verifying": "magenta",
        "completed": "green",
        "failed": "red",
        "cancelled": "dim",
    }
    color = status_colors.get(session.status.value, "white")

    console.print(
        Panel(
            f"[bold]Session ID:[/bold] {session.session_id}\n"
            f"[bold]Task:[/bold] {session.task}\n"
            f"[bold]Status:[/bold] [{color}]{session.status.value.upper()}[/{color}]\n"
            f"[bold]Progress:[/bold] {session.completed_steps}/{session.total_steps} "
            f"({session.progress_pct:.0f}%)\n"
            f"[bold]Duration:[/bold] {session.duration_s}s\n"
            f"[bold]Files modified:[/bold] {len(session.files_modified)}",
            title="[bold cyan]Session Detail[/bold cyan]",
            border_style=color,
        )
    )

    if session.error:
        console.print(f"\n[red bold]Error:[/red bold] {session.error}")

    # Steps table
    if session.steps:
        step_table = Table(title="Steps", show_lines=True)
        step_table.add_column("#", width=4, justify="right")
        step_table.add_column("Description", max_width=40)
        step_table.add_column("Tool", width=12)
        step_table.add_column("Status", width=12)
        step_table.add_column("Retries", width=8, justify="right")
        step_table.add_column("Time", width=10, justify="right")

        step_styles = {
            "pending": "dim",
            "running": "yellow",
            "completed": "green",
            "failed": "red",
            "skipped": "dim",
        }

        for i, step in enumerate(session.steps, 1):
            ss = step_styles.get(step.status.value, "white")
            step_table.add_row(
                str(i),
                step.description[:40],
                step.tool_name or "-",
                f"[{ss}]{step.status.value}[/{ss}]",
                str(step.retries),
                f"{step.duration_ms:.0f}ms",
            )
        console.print(step_table)

    # Files
    if session.files_modified:
        console.print("\n[bold]Files modified:[/bold]")
        for f in session.files_modified:
            console.print(f"  [cyan]→[/cyan] {f}")


@session_cmds.command("cancel")
@click.argument("session_id")
def session_cancel(session_id: str) -> None:
    """Cancel a running session."""
    store = _get_store()

    if store.cancel(session_id):
        console.print(
            f"[green]✓[/green] Session {session_id[:8]} cancelled"
        )
    else:
        console.print(
            f"[red]Cannot cancel session {session_id[:8]} "
            "(not found or already terminal)[/red]"
        )
        sys.exit(1)


@session_cmds.command("logs")
@click.argument("session_id")
@click.option("--tail", "-n", default=50, help="Number of log lines.")
def session_logs(session_id: str, tail: int) -> None:
    """Show execution logs for a session."""
    store = _get_store()
    session = store.get(session_id)

    if session is None:
        console.print(f"[red]Session not found: {session_id}[/red]")
        sys.exit(1)

    console.print(
        f"[bold cyan]Logs for session {session.session_id[:8]}[/bold cyan] "
        f"({session.status.value})\n"
    )

    if not session.logs:
        console.print("[dim]No logs available.[/dim]")
        return

    for log_line in session.logs[-tail:]:
        console.print(f"  {log_line}")
