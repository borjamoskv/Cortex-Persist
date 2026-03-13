"""MOSKV-Aether — SQLite-backed task queue.

Thread-safe O(1) pop via atomic UPDATE+SELECT.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from cortex.aether.models import AgentTask, TaskStatus

__all__ = ["TaskQueue"]

logger = logging.getLogger("cortex.aether.queue")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_tasks (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    repo_path       TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'cli',
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    plan            TEXT NOT NULL DEFAULT '',
    result          TEXT NOT NULL DEFAULT '',
    branch          TEXT NOT NULL DEFAULT '',
    pr_url          TEXT NOT NULL DEFAULT '',
    error           TEXT NOT NULL DEFAULT '',
    github_issue_number INTEGER,
    github_repo     TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_tasks_status
    ON agent_tasks (status, created_at);
"""


class TaskQueue:
    """Thread-safe SQLite task queue for Aether agent tasks."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".cortex" / "aether.db"
            # Auto-migrate legacy jules.db if it exists
            legacy_path = Path.home() / ".cortex" / "jules.db"
            if not db_path.exists() and legacy_path.exists():
                legacy_path.rename(db_path)
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:  # noqa: BLE001 — rollback transaction before raising
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def enqueue(self, task: AgentTask) -> AgentTask:
        """Add a task to the queue. Returns the task with db-confirmed state."""
        now = datetime.now(timezone.utc).isoformat()
        task.created_at = now
        task.updated_at = now
        task.status = TaskStatus.PENDING

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_tasks
                    (id, title, description, repo_path, source, status,
                     created_at, updated_at, plan, result, branch, pr_url,
                     error, github_issue_number, github_repo)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id, task.title, task.description, task.repo_path,
                    task.source, task.status, task.created_at, task.updated_at,
                    task.plan, task.result, task.branch, task.pr_url,
                    task.error, task.github_issue_number, task.github_repo,
                ),
            )
        logger.info("✅ Enqueued task [%s] — %s", task.id, task.title)
        return task

    def pop_next(self) -> AgentTask | None:
        """Atomically pop the oldest pending task and mark it as planning.

        Uses SQLite 3.35+ UPDATE ... RETURNING for true process-level O(1)
        atomicity, bypassing the need for thread locks. Zero race conditions
        even if multiple MOSKV-1 agents pull from the queue simultaneously.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._conn() as conn:
            row = conn.execute(
                """
                UPDATE agent_tasks
                SET status = ?, updated_at = ?
                WHERE id = (
                    SELECT id FROM agent_tasks
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 1
                )
                RETURNING *
                """,
                (TaskStatus.PLANNING, now),
            ).fetchone()

            if not row:
                return None

            return AgentTask.from_dict(dict(row))

    def update(self, task_id: str, **fields) -> None:
        """Update arbitrary fields on a task."""
        if not fields:
            return
        now = datetime.now(timezone.utc).isoformat()
        fields["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [task_id]
        with self._conn() as conn:
            conn.execute(
                f"UPDATE agent_tasks SET {set_clause} WHERE id = ?", values
            )

    def get(self, task_id: str) -> AgentTask | None:
        """Fetch a task by ID."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if row is None:
            return None
        return AgentTask.from_dict(dict(row))

    def list_tasks(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[AgentTask]:
        """List tasks, optionally filtered by status."""
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM agent_tasks WHERE status = ? "
                    "ORDER BY id DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM agent_tasks ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [AgentTask.from_dict(dict(r)) for r in rows]

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending or running task. Returns True if cancelled."""
        with self._conn() as conn:
            result = conn.execute(
                """
                UPDATE agent_tasks
                SET status = ?, updated_at = ?
                WHERE id = ? AND status IN ('pending', 'planning', 'executing',
                                             'critiquing', 'testing')
                """,
                (TaskStatus.CANCELLED, datetime.now(timezone.utc).isoformat(), task_id),
            )
        cancelled = result.rowcount > 0
        if cancelled:
            logger.info("🚫 Cancelled task [%s]", task_id)
        return cancelled

    @property
    def pending_count(self) -> int:
        with self._conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM agent_tasks WHERE status = 'pending'"
            ).fetchone()[0]
