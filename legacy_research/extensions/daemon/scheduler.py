# [C5-REAL] Exergy-Maximized
"""SovereignScheduler - Async cron/interval task scheduler with SQLite persistence.

Runs recurring and one-shot tasks on the daemon's single event loop.
Survives restarts via SQLite WAL-mode persistence.

Architecture:
    ┌───────────────────────────────────────┐
    │  SovereignScheduler                    │
    │  ┌──────────┐  ┌──────────────────┐   │
    │  │ Interval │  │ Cron (croniter)  │   │
    │  │  Tasks   │  │    Tasks         │   │
    │  └────┬─────┘  └────┬─────────────┘   │
    │       └──────┬───────┘                 │
    │         EventBus.publish()             │
    │         HotStateDB.set()               │
    └───────────────────────────────────────┘

Derivation: Ω₃ (Cycle Law) - Compound_Yield = Σ(Yield_i × S^d_i)
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
import time
from collections.abc import Callable, Coroutine
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.daemon.scheduler")

__all__ = ["ScheduleEntry", "SovereignScheduler"]

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS schedules (
    name        TEXT PRIMARY KEY,
    kind        TEXT NOT NULL DEFAULT 'interval',   -- 'interval' | 'cron' | 'oneshot'
    interval_s  REAL,
    cron_expr   TEXT,
    priority    INTEGER NOT NULL DEFAULT 5,
    enabled     INTEGER NOT NULL DEFAULT 1,
    last_run_at TEXT,
    next_run_at TEXT,
    run_count   INTEGER NOT NULL DEFAULT 0,
    total_ms    REAL NOT NULL DEFAULT 0.0,
    last_error  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


@dataclass
class ScheduleEntry:
    """Represents a scheduled task."""

    name: str
    kind: str = "interval"
    interval_s: float | None = None
    cron_expr: str | None = None
    priority: int = 5
    enabled: bool = True
    last_run_at: str | None = None
    next_run_at: str | None = None
    run_count: int = 0
    total_ms: float = 0.0
    last_error: str = ""
    created_at: str = ""
    updated_at: str = ""


# Type alias for task factories
TaskFactory = Callable[[], Coroutine[Any, Any, Any]]


class SovereignScheduler:
    """Async cron/interval scheduler backed by SQLite.

    Usage:
        scheduler = SovereignScheduler()

        async def my_task():
            print("tick")

        scheduler.add_recurring("health_check", lambda: my_task(), interval_s=300)
        await scheduler.run()  # blocks forever
    """

    __slots__ = (
        "_db_path",
        "_event_bus",
        "_hot_state",
        "_running",
        "_stop_event",
        "_tasks",
        "_tick_interval",
    )

    def __init__(
        self,
        db_path: Path | str | None = None,
        event_bus: Any | None = None,
        hot_state: Any | None = None,
        tick_interval: float = 5.0,
    ) -> None:
        if db_path is None:
            db_path = Path.home() / ".cortex" / "scheduler.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._event_bus = event_bus
        self._hot_state = hot_state
        self._tick_interval = tick_interval
        self._running = False
        self._stop_event = asyncio.Event()
        self._tasks: dict[str, TaskFactory] = {}
        self._init_db()

    @contextmanager
    def _conn(self):
        from legacy_research.database.core import connect

        conn = connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    # ─── Registration ─────────────────────────────────────────────

    def add_recurring(
        self,
        name: str,
        coro_factory: TaskFactory,
        interval_s: float,
        *,
        priority: int = 5,
    ) -> ScheduleEntry:
        """Register a recurring interval task."""
        self._tasks[name] = coro_factory
        now = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        entry = ScheduleEntry(
            name=name,
            kind="interval",
            interval_s=interval_s,
            priority=priority,
            created_at=now,
            updated_at=now,
        )
        self._upsert(entry)
        logger.info("Registered recurring task: %s (every %.0fs)", name, interval_s)
        return entry

    def add_cron(
        self,
        name: str,
        coro_factory: TaskFactory,
        cron_expr: str,
        *,
        priority: int = 5,
    ) -> ScheduleEntry:
        """Register a cron-expression task (requires croniter)."""
        self._tasks[name] = coro_factory
        now = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        next_run = self._next_cron_time(cron_expr)
        entry = ScheduleEntry(
            name=name,
            kind="cron",
            cron_expr=cron_expr,
            priority=priority,
            next_run_at=next_run,
            created_at=now,
            updated_at=now,
        )
        self._upsert(entry)
        logger.info("Registered cron task: %s (%s)", name, cron_expr)
        return entry

    def add_oneshot(
        self,
        name: str,
        coro_factory: TaskFactory,
        run_at: str | None = None,
        *,
        priority: int = 5,
    ) -> ScheduleEntry:
        """Register a one-shot task."""
        self._tasks[name] = coro_factory
        now = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        entry = ScheduleEntry(
            name=name,
            kind="oneshot",
            priority=priority,
            next_run_at=run_at or now,
            created_at=now,
            updated_at=now,
        )
        self._upsert(entry)
        logger.info("Registered one-shot task: %s", name)
        return entry

    def cancel(self, name: str) -> bool:
        """Disable a scheduled task."""
        self._tasks.pop(name, None)
        with self._conn() as conn:
            result = conn.execute(
                "UPDATE schedules SET enabled = 0, updated_at = ? WHERE name = ?",
                (datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(), name),
            )
        cancelled = result.rowcount > 0
        if cancelled:
            logger.info("Cancelled schedule: %s", name)
        return cancelled

    def list_schedules(self) -> list[ScheduleEntry]:
        """List all registered schedules."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM schedules ORDER BY priority ASC, name ASC"
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    # ─── Main Loop ────────────────────────────────────────────────

    async def run(self) -> None:
        """Main scheduler loop. Blocks until stop() is called."""
        self._running = True
        logger.info("SovereignScheduler started (tick=%.1fs)", self._tick_interval)

        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error("Scheduler tick error: %s", e)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._tick_interval,
                )
                break  # stop_event was set
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)
        # normal tick timeout

        logger.info("SovereignScheduler stopped")

    async def stop(self) -> None:
        """Signal the scheduler to stop."""
        self._running = False
        self._stop_event.set()

    async def _tick(self) -> None:
        """Evaluate all schedules and fire due tasks."""
        now = datetime.fromtimestamp(time.time(), tz=timezone.utc)
        now_iso = now.isoformat()

        with self._conn() as conn:
            due = conn.execute(
                """
                SELECT * FROM schedules
                WHERE enabled = 1
                  AND (next_run_at IS NULL OR next_run_at <= ?)
                ORDER BY priority ASC
                """,
                (now_iso,),
            ).fetchall()

        for row in due:
            entry = self._row_to_entry(row)
            factory = self._tasks.get(entry.name)
            if factory is None:
                continue

            start = time.monotonic()
            error = ""
            try:
                await asyncio.wait_for(factory(), timeout=300.0)
            except asyncio.TimeoutError:
                error = "Timeout (300s)"
                logger.warning("Task %s timed out", entry.name)
            except Exception as e:
                error = str(e)
                logger.error("Task %s failed: %s", entry.name, e)

            elapsed_ms = (time.monotonic() - start) * 1000

            # Update schedule state
            next_run = self._compute_next_run(entry)
            with self._conn() as conn:
                conn.execute(
                    """
                    UPDATE schedules SET
                        last_run_at = ?,
                        next_run_at = ?,
                        run_count = run_count + 1,
                        total_ms = total_ms + ?,
                        last_error = ?,
                        updated_at = ?,
                        enabled = CASE WHEN kind = 'oneshot' THEN 0 ELSE enabled END
                    WHERE name = ?
                    """,
                    (now_iso, next_run, elapsed_ms, error, now_iso, entry.name),
                )

            # Publish event
            if self._event_bus is not None:
                try:
                    await self._event_bus.publish(
                        "schedule.completed",
                        {
                            "task": entry.name,
                            "elapsed_ms": round(elapsed_ms, 1),
                            "error": error,
                            "source": "scheduler",
                        },
                    )
                except Exception as e:
                    logger.debug(
                        "Scheduler event bus publish failed: %s", e, exc_info=True
                    )  # bus errors must not kill scheduler

            # Hot state update
            if self._hot_state is not None:
                try:
                    self._hot_state.set(
                        f"schedule:{entry.name}:last_run",
                        {
                            "at": now_iso,
                            "ms": round(elapsed_ms, 1),
                            "ok": not error,
                        },
                    )
                except Exception as e:
                    logger.debug("Scheduler hot state set failed: %s", e, exc_info=True)

            level = "✅" if not error else "❌"
            logger.info(
                "%s [%s] completed in %.0fms%s",
                level,
                entry.name,
                elapsed_ms,
                f" - {error}" if error else "",
            )

    # ─── Helpers ──────────────────────────────────────────────────

    def _upsert(self, entry: ScheduleEntry) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO schedules
                    (name, kind, interval_s, cron_expr, priority, enabled,
                     last_run_at, next_run_at, run_count, total_ms,
                     last_error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    kind = excluded.kind,
                    interval_s = excluded.interval_s,
                    cron_expr = excluded.cron_expr,
                    priority = excluded.priority,
                    enabled = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    entry.name,
                    entry.kind,
                    entry.interval_s,
                    entry.cron_expr,
                    entry.priority,
                    1 if entry.enabled else 0,
                    entry.last_run_at,
                    entry.next_run_at,
                    entry.run_count,
                    entry.total_ms,
                    entry.last_error,
                    entry.created_at,
                    entry.updated_at,
                ),
            )

    def _compute_next_run(self, entry: ScheduleEntry) -> str | None:
        now = datetime.fromtimestamp(time.time(), tz=timezone.utc)
        if entry.kind == "interval" and entry.interval_s:
            from datetime import timedelta

            return (now + timedelta(seconds=entry.interval_s)).isoformat()
        if entry.kind == "cron" and entry.cron_expr:
            return self._next_cron_time(entry.cron_expr)
        return None  # oneshot - won't run again

    @staticmethod
    def _next_cron_time(cron_expr: str) -> str:
        """Compute next cron fire time. Falls back to 1h if croniter missing."""
        try:
            from croniter import croniter

            return (
                croniter(cron_expr, datetime.fromtimestamp(time.time(), tz=timezone.utc))
                .get_next(datetime)
                .isoformat()
            )
        except ImportError:
            from datetime import timedelta

            return (
                datetime.fromtimestamp(time.time(), tz=timezone.utc) + timedelta(hours=1)
            ).isoformat()

    @staticmethod
    def _row_to_entry(row) -> ScheduleEntry:
        return ScheduleEntry(
            name=row["name"],
            kind=row["kind"],
            interval_s=row["interval_s"],
            cron_expr=row["cron_expr"],
            priority=row["priority"],
            enabled=bool(row["enabled"]),
            last_run_at=row["last_run_at"],
            next_run_at=row["next_run_at"],
            run_count=row["run_count"],
            total_ms=row["total_ms"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
