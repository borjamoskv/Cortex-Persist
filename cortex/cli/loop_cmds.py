"""CORTEX Execution Loop — Task Input → Result Output → Auto-Persistence.

Durability Architecture (Ω₃ Byzantine Default):
    ┌─────────────────────────────────────────────────────────┐
    │                CORTEX EXECUTION LOOP                    │
    │                                                         │
    │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
    │  │  INPUT   │→ │ EXECUTE  │→ │  PERSIST (2-layer)   │  │
    │  │  (task)  │  │ (keter)  │  │                      │  │
    │  └──────────┘  └──────────┘  │  C5 🟢 Supervisor    │  │
    │       ↑                      │    every 60s         │  │
    │       └──────────────────────│  C4 🔵 atexit        │  │
    │                              │    best-effort       │  │
    │                              └──────────────────────┘  │
    └─────────────────────────────────────────────────────────┘

  GUARANTEE (C5): PersistSupervisor — external thread, persists every
    PERSIST_INTERVAL seconds. Survives SIGTERM. Max data loss = interval.
  FALLBACK (C4): atexit — fires on clean process exit only. Does NOT
    survive SIGKILL, OOM, kernel panic, or CPython segfault.

  Rule: Never invert the confidence order. The supervisor is primary.

DERIVATION: Ω₃ (Byzantine Default) + Ω₅ (Antifragile by Default)

Usage:
    cortex loop [--project PROJECT] [--mode interactive|batch]
    cortex loop --task "Implement auth module" --project my-app
"""

from __future__ import annotations

import logging

import click
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from cortex.cli.common import DEFAULT_DB, cli, console
from cortex.cli.loop_engine import ExecutionLoop
from cortex.cli.loop_models import TaskStatus

__all__ = ["loop"]

logger = logging.getLogger("cortex.loop")

# ─── Industrial Noir Palette ──────────────────────────────────────────
CYBER_LIME = "#CCFF00"
ELECTRIC_VIOLET = "#6600FF"
ABYSSAL_BLACK = "#0A0A0A"
YINMN_BLUE = "#2E5090"
GOLD = "#D4AF37"


# Models → cortex.cli.loop_models
# ExecutionLoop + PersistSupervisor → cortex.cli.loop_engine


# ─── CLI Commands ─────────────────────────────────────────────────────


@cli.command("loop")
@click.option(
    "--project",
    "-p",
    default="cortex",
    help="Project scope for persistence",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["interactive", "batch"]),
    default="interactive",
    help="Execution mode",
)
@click.option(
    "--task",
    "-t",
    default=None,
    help="Single task to execute (batch mode)",
)
@click.option(
    "--no-persist",
    is_flag=True,
    default=False,
    help="Disable auto-persistence",
)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def loop(project: str, mode: str, task: str | None, no_persist: bool, db: str) -> None:
    """Sovereign Execution Loop — Task → Execute → Persist → Repeat.

    Interactive mode: REPL with continuous task execution.
    Batch mode: Execute a single task and exit.

    \b
    Examples:
        cortex loop -p my-app
        cortex loop -t "Implement auth" -p my-app
        cortex loop --mode batch -t "Fix bug #42"
    """
    loop_engine = ExecutionLoop(
        project=project,
        db=db,
        auto_persist=not no_persist,
    )

    try:
        if mode == "batch" or task:
            _run_batch(loop_engine, task or "")
        else:
            _run_interactive(loop_engine)
    finally:
        loop_engine.close()


def _run_batch(loop_engine: ExecutionLoop, task: str) -> None:
    """Execute a single task and exit."""
    if not task:
        console.print("[red]✗ --task is required in batch mode[/]")
        return

    console.print(
        Panel(
            f"[bold white]Executing:[/] {task}",
            title=f"[bold {CYBER_LIME}]CORTEX LOOP • BATCH[/]",
            border_style=YINMN_BLUE,
        )
    )

    result = loop_engine.execute_task(task)
    loop_engine.render_result(result)  # type: ignore[reportAttributeAccessIssue]


def _run_interactive(loop_engine: ExecutionLoop) -> None:
    """Interactive REPL execution loop."""
    _show_banner(loop_engine._project)

    while True:
        try:
            console.print()
            loop_engine.render_session_status()  # type: ignore[reportAttributeAccessIssue]

            task = Prompt.ask(
                f"\n[bold {CYBER_LIME}]⚡ TASK[/]",
                console=console,
            )

            action = _dispatch_command(loop_engine, task)
            if action == "break":
                break
            if action == "continue":
                continue

            # Execute task
            with console.status(f"[{ELECTRIC_VIOLET}]Executing...[/]", spinner="dots"):
                result = loop_engine.execute_task(task)

            loop_engine.render_result(result)  # type: ignore[reportAttributeAccessIssue]

        except KeyboardInterrupt:
            console.print(f"\n[{GOLD}]⊘ Interrupted. Type 'exit' to close.[/]")
            continue
        except EOFError:
            _handle_exit(loop_engine)
            break


def _dispatch_command(loop_engine: ExecutionLoop, task: str) -> str | None:
    """Dispatch built-in commands. Returns 'break', 'continue', or None."""
    stripped = task.strip().lower()

    if stripped in ("exit", "quit", "q", ":q"):
        _handle_exit(loop_engine)
        return "break"
    if stripped in ("status", ":s"):
        _handle_status(loop_engine)
        return "continue"
    if stripped in ("history", ":h"):
        _handle_history(loop_engine)
        return "continue"
    if stripped.startswith("ghost ") or stripped.startswith(":g "):
        ghost_desc = task.split(" ", 1)[1] if " " in task else ""
        _handle_ghost(loop_engine, ghost_desc)
        return "continue"
    if stripped in ("help", ":?", "?"):
        _show_help()
        return "continue"
    if not stripped:
        return "continue"

    return None


# ─── Interactive Handlers ─────────────────────────────────────────────


def _show_banner(project: str) -> None:
    """Display the execution loop banner."""
    banner = Text()
    banner.append("╔══════════════════════════════════════════╗\n", style=YINMN_BLUE)
    banner.append("║  ", style=YINMN_BLUE)
    banner.append("CORTEX EXECUTION LOOP", style=f"bold {CYBER_LIME}")
    banner.append("                 ║\n", style=YINMN_BLUE)
    banner.append("║  ", style=YINMN_BLUE)
    banner.append("Task → Execute → Persist → Repeat", style="dim white")
    banner.append("      ║\n", style=YINMN_BLUE)
    banner.append("╚══════════════════════════════════════════╝", style=YINMN_BLUE)

    console.print(
        Panel(
            banner,
            title=f"[bold {GOLD}]⚡ SOVEREIGN LOOP[/]",
            subtitle=f"[dim]project: {project} │ type 'help' for commands[/dim]",
            border_style=ELECTRIC_VIOLET,
            padding=(1, 2),
        )
    )


def _show_help() -> None:
    """Display help for interactive commands."""
    help_table = Table(
        title=f"[{CYBER_LIME}]Loop Commands[/]",
        border_style=YINMN_BLUE,
        show_header=True,
        header_style=f"bold {CYBER_LIME}",
    )
    help_table.add_column("Command", style="bold white", width=20)
    help_table.add_column("Description", style="dim white")

    commands = [
        ("<any text>", "Execute as task → auto-persist result"),
        ("ghost <desc>", "Mark incomplete work for continuation"),
        ("status / :s", "Show current session statistics"),
        ("history / :h", "Show task execution history"),
        ("help / :?", "Show this help"),
        ("exit / quit / :q", "Close loop (persists session summary)"),
    ]
    for cmd, desc in commands:
        help_table.add_row(cmd, desc)

    console.print(help_table)


def _handle_exit(loop_engine: ExecutionLoop) -> None:
    """Handle graceful exit."""
    session = loop_engine._session
    console.print(
        Panel(
            f"[bold white]Session Complete[/]\n\n"
            f"[{CYBER_LIME}]✓[/] Tasks completed: {session.tasks_completed}\n"
            f"[red]✗[/] Tasks failed: {session.tasks_failed}\n"
            f"[{GOLD}]💾[/] Facts persisted: {session.total_persisted}",
            title=f"[bold {CYBER_LIME}]LOOP CLOSED[/]",
            border_style=YINMN_BLUE,
            padding=(1, 2),
        )
    )


def _handle_status(loop_engine: ExecutionLoop) -> None:
    """Show detailed session status."""
    session = loop_engine._session

    table = Table(
        title=f"[{CYBER_LIME}]Session Status[/]",
        border_style=YINMN_BLUE,
    )
    table.add_column("Metric", style=f"bold {CYBER_LIME}")
    table.add_column("Value", style="white")

    table.add_row("Project", session.project)
    table.add_row("Source", session.source)
    table.add_row("Started", session.started_at[:19])
    table.add_row("Tasks Completed", str(session.tasks_completed))
    table.add_row("Tasks Failed", str(session.tasks_failed))
    table.add_row("Facts Persisted", str(session.total_persisted))
    table.add_row("Active", "✓" if session.active else "✗")

    console.print(table)


def _status_style_for(status: TaskStatus) -> str:
    """Resolve Rich style string for a task status."""
    _STYLES: dict[TaskStatus, str] = {
        TaskStatus.COMPLETED: f"bold {CYBER_LIME}",
        TaskStatus.FAILED: "bold red",
    }
    return _STYLES.get(status, f"bold {GOLD}")


def _handle_history(loop_engine: ExecutionLoop) -> None:
    """Show task execution history."""
    results = loop_engine._session.results
    if not results:
        console.print("[dim]No tasks executed yet.[/]")
        return

    table = Table(
        title=f"[{CYBER_LIME}]Execution History ({len(results)} tasks)[/]",
        border_style=YINMN_BLUE,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Task", style="white", width=40)
    table.add_column("Status", width=10)
    table.add_column("Duration", style=f"dim {CYBER_LIME}", width=10)
    table.add_column("Persisted", style=f"dim {GOLD}", width=10)

    for i, r in enumerate(results, 1):
        status_style = _status_style_for(r.status)
        status_text = f"[{status_style}]{r.status.value}[/]"
        task_preview = r.task[:37] + "..." if len(r.task) > 40 else r.task
        persisted = str(r.persisted_ids) if r.persisted_ids else "—"

        table.add_row(
            str(i),
            task_preview,
            status_text,
            f"{r.duration_ms:.0f}ms",
            persisted,
        )

    console.print(table)


def _handle_ghost(loop_engine: ExecutionLoop, description: str) -> None:
    """Register incomplete work as a ghost."""
    if not description.strip():
        console.print("[red]✗ Ghost requires a description[/]")
        return

    loop_engine._persist_ghost(description)
    console.print(f"[{GOLD}]👻 Ghost registered (async):[/] {description}")
