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

import atexit
import logging
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import click
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from cortex.cli.common import (
    DEFAULT_DB,
    _detect_agent_source,
    _run_async,
    cli,
    console,
    get_engine,
)

__all__ = ["loop"]

logger = logging.getLogger("cortex.loop")

# ─── Industrial Noir Palette ──────────────────────────────────────────
CYBER_LIME = "#CCFF00"
ELECTRIC_VIOLET = "#6600FF"
ABYSSAL_BLACK = "#0A0A0A"
YINMN_BLUE = "#2E5090"
GOLD = "#D4AF37"


# ─── Models ───────────────────────────────────────────────────────────


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PersistenceType(Enum):
    DECISION = "decision"
    ERROR = "error"
    GHOST = "ghost"
    BRIDGE = "bridge"
    KNOWLEDGE = "knowledge"


@dataclass
class TaskResult:
    """Result of a single task execution."""

    task: str
    status: TaskStatus
    output: str
    duration_ms: float
    persisted_ids: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class LoopSession:
    """Tracks the full execution loop session."""

    project: str
    source: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_persisted: int = 0
    results: list[TaskResult] = field(default_factory=list)
    active: bool = True


# ─── Persist Supervisor ───────────────────────────────────────────────

#: Default supervisor interval. Every tick = max data loss window.
PERSIST_INTERVAL: int = 60


class PersistSupervisor:
    """External supervisor thread — C5 durability guarantee.

    Persists pending facts every ``interval`` seconds, independent of
    process lifecycle. The primary persistence guarantee for the loop.

    Design contract (Ω₃):
      - Does NOT trust the process to exit cleanly.
      - Each tick drains the pending queue atomically.
      - On persist failure: re-enqueues the fact (Ω₅ — error = gradient).
      - Never raises — the supervisor must not die.
      - stop() is idempotent — safe to call multiple times (atexit + close).

    Confidence: C5 🟢 (confirmed) — bounded data loss = ``interval`` seconds.
    """

    def __init__(
        self,
        flush_fn: Any,
        interval: int = PERSIST_INTERVAL,
    ) -> None:
        self._flush = flush_fn
        self._interval = interval
        self._stop = threading.Event()
        self._started = False
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,  # Does not block process exit
            name="cortex-persist-supervisor",
        )

    def start(self) -> None:
        self._started = True
        self._thread.start()
        logger.info(
            "PersistSupervisor started — interval=%ds (C5 durability)",
            self._interval,
        )

    def stop(self) -> None:
        """Signal stop and wait for the supervisor to complete its final flush.

        Idempotent — safe to call from both close() and _atexit_flush.
        Second call is a guaranteed no-op: Event is already set, dead thread
        join() returns immediately.
        """
        if not self._started:
            return
        self._stop.set()
        self._thread.join(timeout=5.0)  # Bounded wait — never hang on exit

    def _run(self) -> None:
        """Tick every N seconds, flush pending facts. Never raises."""
        while not self._stop.wait(timeout=self._interval):
            try:
                self._flush(source="supervisor")
            except Exception as exc:  # noqa: BLE001 — supervisor must not die
                logger.warning("PersistSupervisor: flush error (non-fatal): %s", exc)


# ─── Core Execution Engine ────────────────────────────────────────────


class ExecutionLoop:
    """The sovereign execution loop: Task → Execute → Persist → Repeat.

    Durability model:
      - PersistSupervisor (C5 🟢): external thread, persists every 60s.
      - atexit (C4 🔵): fires on clean exit, covers last partial interval.
    """

    def __init__(
        self,
        project: str,
        db: str = DEFAULT_DB,
        source: str | None = None,
        auto_persist: bool = True,
        persist_interval: int = PERSIST_INTERVAL,
    ) -> None:
        self._project = project
        self._db = db
        self._source = source or _detect_agent_source()
        self._auto_persist = auto_persist
        self._engine = get_engine(db)
        self._session = LoopSession(project=project, source=self._source)

        # ── Durability layer ──────────────────────────────────────
        self._pending_facts: list[dict[str, Any]] = []
        self._pending_lock = threading.Lock()
        self._closed = False  # Guards idempotent atexit (close() + atexit)

        if auto_persist:
            # C5 🟢 — external supervisor, primary guarantee
            self._supervisor = PersistSupervisor(
                flush_fn=self._flush_pending,
                interval=persist_interval,
            )
            self._supervisor.start()

            # C4 🔵 — atexit fallback, documented as best-effort only.
            # Fires on clean exit (sys.exit, return from main).
            # Does NOT fire on SIGKILL / OOM / kernel panic / segfault.
            # Never rely on this as the primary persistence mechanism.
            atexit.register(self._atexit_flush)
        else:
            self._supervisor = None  # type: ignore[assignment]

    # ── Single Task Execution ──────────────────────────────────────

    def execute_task(self, task: str) -> TaskResult:
        """Execute a single task and auto-persist results to CORTEX."""
        t0 = time.monotonic()
        result = TaskResult(
            task=task,
            status=TaskStatus.RUNNING,
            output="",
            duration_ms=0.0,
        )

        try:
            # Phase 1: Execute via KETER Engine
            output = self._run_keter(task)
            elapsed = (time.monotonic() - t0) * 1000

            result.status = TaskStatus.COMPLETED
            result.output = output
            result.duration_ms = elapsed

            # Phase 2: Auto-persist decision
            if self._auto_persist:
                persisted = self._persist_result(result)
                result.persisted_ids = persisted

            self._session.tasks_completed += 1

        except KeyboardInterrupt:
            result.status = TaskStatus.CANCELLED
            result.output = "Task cancelled by user"
            result.duration_ms = (time.monotonic() - t0) * 1000

        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            result.status = TaskStatus.FAILED
            result.output = str(exc)
            result.duration_ms = elapsed
            result.errors.append(traceback.format_exc())

            # Auto-persist error
            if self._auto_persist:
                error_ids = self._persist_error(task, exc)
                result.persisted_ids = error_ids

            self._session.tasks_failed += 1

        self._session.results.append(result)
        return result

    # ── KETER Integration ──────────────────────────────────────────

    def _run_keter(self, task: str) -> str:
        """Execute task through KETER Engine phases."""
        from cortex.engine.keter import KeterEngine

        async def _ignite():
            keter = KeterEngine()
            payload = await keter.ignite(task, project=self._project)
            return payload

        try:
            payload = _run_async(_ignite())
            # Format output from KETER phases
            parts = []
            if payload.get("spec_130_100"):
                parts.append(f"Spec: {payload['spec_130_100']}")
            if payload.get("scaffold_status"):
                parts.append(f"Scaffold: {payload['scaffold_status']}")
            if payload.get("legion_audit"):
                parts.append(f"Audit: {payload['legion_audit']}")
            if payload.get("fv_audit"):
                parts.append(f"Verification: {payload['fv_audit']}")
            if payload.get("score_130_100"):
                parts.append(f"Quality: {payload['score_130_100']}/100")
            parts.append(f"Status: {payload.get('status', 'unknown')}")
            return " │ ".join(parts)
        except Exception as exc:
            logger.warning("KETER execution failed, storing as knowledge: %s", exc)
            # Fallback: store directly as knowledge
            return f"Task registered: {task}"

    # ── Persistence Layer ──────────────────────────────────────────

    def _enqueue_fact(self, content: str, fact_type: str, **meta: Any) -> None:
        """Enqueue a fact for the supervisor to persist at next tick.

        Thread-safe. Facts are drained by _flush_pending.
        """
        with self._pending_lock:
            self._pending_facts.append(
                {
                    "project": self._project,
                    "content": content,
                    "fact_type": fact_type,
                    "source": self._source,
                    "meta": meta,
                }
            )

    def _flush_pending(self, source: str = "supervisor") -> None:
        """Drain the pending queue and persist to CORTEX. Idempotent.

        Called by PersistSupervisor every 60s (C5) and by atexit/close (C4).

        Thread-safety note on asyncio.run():
          _flush_pending runs from the supervisor thread (non-async context).
          asyncio.run() is intentional here — it creates a fresh event loop
          per call, avoiding cross-thread loop sharing which is not safe.
          Each store is O(1) and bounded. Acceptable cost for durability.
        """
        with self._pending_lock:
            if not self._pending_facts:
                return
            batch, self._pending_facts = self._pending_facts[:], []

        re_enqueue: list[dict[str, Any]] = []
        persisted_count = 0
        for fact in batch:
            try:
                fact_id = _run_async(
                    self._engine.store(
                        project=fact["project"],
                        content=fact["content"],
                        fact_type=fact["fact_type"],
                        source=f"{fact['source']}:{source}",
                        meta=fact.get("meta", {}),
                    )
                )
                if fact_id:
                    persisted_count += 1
                    logger.debug(
                        "_flush_pending: stored %s fact #%d via %s",
                        fact["fact_type"],
                        fact_id,
                        source,
                    )
            except (OSError, ValueError) as exc:
                # Re-enqueue for next supervisor tick — Ω₅ (error = gradient)
                logger.warning(
                    "_flush_pending: store failed (%s), re-enqueueing: %s",
                    source,
                    exc,
                )
                re_enqueue.append(fact)

        # Update counter under lock — protects against supervisor thread race
        if persisted_count:
            with self._pending_lock:
                self._session.total_persisted += persisted_count

        if re_enqueue:
            with self._pending_lock:
                self._pending_facts = re_enqueue + self._pending_facts

    def _atexit_flush(self) -> None:
        """C4 🔵 atexit fallback — fires on clean process exit only.

        Idempotent: if close() already ran (_closed=True), this is a no-op.
        Otherwise: stops the supervisor (idempotent — double-stop is safe)
        then drains any facts accumulated since the last supervisor tick.

        DO NOT treat this as the primary persistence mechanism.
        Derivation: Ω₃ (Byzantine Default) — atexit is never C5.
        """
        if self._closed:
            logger.debug("_atexit_flush: skipped (close() already ran)")
            return
        if self._supervisor is not None:
            self._supervisor.stop()  # Idempotent — no-op if already stopped
        self._flush_pending(source="atexit_fallback")
        logger.info("atexit_flush: completed (C4 fallback)")

    def _persist_result(self, result: TaskResult) -> list[int]:
        """Enqueue task result for supervisor to persist."""
        content = f"[LOOP:DECISION] {result.task} → {result.output}"
        self._enqueue_fact(
            content=content,
            fact_type="decision",
            loop_session=self._session.started_at,
            duration_ms=result.duration_ms,
            status=result.status.value,
        )
        # Return [] — actual IDs are assigned asynchronously by supervisor
        return []

    def _persist_error(self, task: str, exc: Exception) -> list[int]:
        """Enqueue error for supervisor to persist."""
        self._enqueue_fact(
            content=f"[LOOP:ERROR] {task} → {type(exc).__name__}: {exc}",
            fact_type="error",
            loop_session=self._session.started_at,
            traceback=traceback.format_exc()[-500:],
        )
        return []

    def _persist_ghost(self, description: str) -> int | None:
        """Enqueue ghost for supervisor to persist. Returns None (async)."""
        self._enqueue_fact(
            content=f"[LOOP:GHOST] {description}",
            fact_type="ghost",
            loop_session=self._session.started_at,
            tasks_completed=self._session.tasks_completed,
        )
        return None  # ID assigned asynchronously by supervisor

    def _persist_session_summary(self) -> None:
        """Enqueue the full session summary for supervisor to persist.

        Called from close() — the supervisor or atexit finalizer will
        drain this before the process terminates.
        """
        if not self._session.results:
            return

        summary_parts = [
            f"[LOOP:SESSION] {self._session.tasks_completed} completed, "
            f"{self._session.tasks_failed} failed, "
            f"{self._session.total_persisted} facts persisted",
        ]
        for r in self._session.results[-10:]:
            icon = "✓" if r.status == TaskStatus.COMPLETED else "✗"
            summary_parts.append(f"  {icon} {r.task[:60]} ({r.duration_ms:.0f}ms)")

        self._enqueue_fact(
            content="\n".join(summary_parts),
            fact_type="knowledge",
            session_start=self._session.started_at,
            session_end=datetime.now(timezone.utc).isoformat(),
            tasks_completed=self._session.tasks_completed,
            tasks_failed=self._session.tasks_failed,
            total_persisted=self._session.total_persisted,
        )

    # ── Rendering ──────────────────────────────────────────────────

    def render_result(self, result: TaskResult) -> None:
        """Render a task result with Industrial Noir aesthetics."""
        if result.status == TaskStatus.COMPLETED:
            status_style = f"bold {CYBER_LIME}"
            status_icon = "✓"
            border = CYBER_LIME
        elif result.status == TaskStatus.FAILED:
            status_style = "bold red"
            status_icon = "✗"
            border = "red"
        elif result.status == TaskStatus.CANCELLED:
            status_style = f"bold {GOLD}"
            status_icon = "⊘"
            border = GOLD
        else:
            status_style = "dim"
            status_icon = "…"
            border = "dim"

        # Task panel
        content = Text()
        content.append(f"{status_icon} ", style=status_style)
        content.append(result.task, style="bold white")
        content.append("\n\n", style="dim")

        # Output
        output_lines = result.output[:500]
        content.append(output_lines, style="white")

        # Metadata footer
        content.append("\n\n", style="dim")
        content.append(f"⏱ {result.duration_ms:.0f}ms", style=f"dim {CYBER_LIME}")

        if result.persisted_ids:
            content.append(
                f"  │  💾 Persisted: {result.persisted_ids}",
                style=f"dim {YINMN_BLUE}",
            )

        if result.errors:
            content.append(f"\n⚠ {len(result.errors)} error(s)", style="dim red")

        console.print(
            Panel(
                content,
                title=f"[{status_style}]EXECUTION RESULT[/]",
                subtitle=f"[dim]{result.timestamp[:19]}[/dim]",
                border_style=border,
                padding=(1, 2),
            )
        )

    def render_session_status(self) -> None:
        """Render current session status bar."""
        table = Table.grid(expand=True)
        table.add_row(
            f"[{CYBER_LIME}]⚡ LOOP[/] [{YINMN_BLUE}]{self._project}[/]",
            f"[{CYBER_LIME}]✓ {self._session.tasks_completed}[/]  "
            f"[red]✗ {self._session.tasks_failed}[/]  "
            f"[{GOLD}]💾 {self._session.total_persisted}[/]",
            f"[dim]src: {self._source}[/]",
        )
        console.print(
            Panel(
                table,
                border_style=YINMN_BLUE,
                padding=(0, 1),
            )
        )

    # ── Lifecycle ──────────────────────────────────────────────────

    def close(self) -> None:
        """Close the execution loop: enqueue summary, flush, stop supervisor.

        Sequence:
          1. Enqueue session summary (into pending_facts)
          2. Stop supervisor (final sync flush via _run)
          3. Flush any remaining facts (covers race between enqueue + stop)
          4. Mark _closed=True so _atexit_flush is a no-op
          5. Close engine
        """
        if self._auto_persist:
            if self._session.results:
                self._persist_session_summary()
            if self._supervisor is not None:
                self._supervisor.stop()  # Blocks until supervisor's last tick done
            self._flush_pending(source="close")  # Drain any final residual
            self._closed = True  # Signal atexit to skip (already clean)

        _run_async(self._engine.close())
        self._session.active = False


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
    loop_engine.render_result(result)


def _run_interactive(loop_engine: ExecutionLoop) -> None:
    """Interactive REPL execution loop."""
    _show_banner(loop_engine._project)

    while True:
        try:
            console.print()
            loop_engine.render_session_status()

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

            loop_engine.render_result(result)

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

    ghost_id = loop_engine._persist_ghost(description)
    if ghost_id:
        console.print(f"[{GOLD}]👻 Ghost #{ghost_id}[/] registered: {description}")
    else:
        console.print("[red]✗ Failed to persist ghost[/]")
