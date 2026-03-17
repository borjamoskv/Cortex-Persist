"""
Entropic Task Queue.

SQLite WAL-backed queue for storing background tasks intended for the CentauroEngine.
Supports concurrent access, priority levels, and retry logic.
"""

import json
import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger("moskv-daemon.centaur.queue")


class EntropicQueue:
    """Persistent, thread-safe, SQLite WAL-backed task queue."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(
            self.db_path,
            timeout=10,
            isolation_level="IMMEDIATE",  # Write-lock immediately to prevent concurrency issues
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize the queue schema with WAL mode enabled."""
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entropic_queue (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    payload JSON NOT NULL,
                    priority INTEGER DEFAULT 50, -- Lower is higher priority
                    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    retries INTEGER DEFAULT 0,
                    error TEXT
                )
            """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_eq_status_priority ON entropic_queue(status, priority, created_at)"
            )
            conn.commit()

    def push(
        self,
        task_type: str,
        payload: dict[str, Any],
        priority: int = 50,
        task_id: str | None = None,
    ) -> str:
        """Push a new task to the queue."""
        uid = task_id or str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO entropic_queue (id, type, payload, priority, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (uid, task_type, json.dumps(payload), priority, now, now),
            )
            conn.commit()
        logger.debug("Pushed task %s (%s) to Entropic Queue.", uid, task_type)
        return uid

    def pop(self, max_retries: int = 3) -> dict[str, Any] | None:
        """Atomically get the highest priority pending task and mark it as 'processing'."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            # SQLite does not have UPDATE ... RETURNING with LIMIT easily in older versions,
            # but modern SQLite does. Let's do a SELECT then UPDATE to be safe and compatible.
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """
                SELECT id, type, payload, retries 
                FROM entropic_queue 
                WHERE status = 'pending' OR (status = 'failed' AND retries < ?)
                ORDER BY priority ASC, id ASC 
                LIMIT 1
                """,
                (max_retries,),
            )
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return None

            task_id = row["id"]
            conn.execute(
                "UPDATE entropic_queue SET status = 'processing', updated_at = ? WHERE id = ?",
                (now, task_id),
            )
            conn.commit()

            return {
                "id": task_id,
                "type": row["type"],
                "payload": json.loads(row["payload"]),
                "retries": row["retries"],
            }

    def mark_completed(self, task_id: str) -> None:
        """Mark a task as successfully completed."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE entropic_queue SET status = 'completed', updated_at = ? WHERE id = ?",
                (now, task_id),
            )
            conn.commit()
        logger.debug("Task %s completed.", task_id)

    def mark_failed(self, task_id: str, error: str) -> None:
        """Mark a task as failed, incrementing its retry count."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE entropic_queue 
                SET status = 'failed', updated_at = ?, retries = retries + 1, error = ? 
                WHERE id = ?
                """,
                (now, error, task_id),
            )
            conn.commit()
        logger.warning("Task %s failed: %s", task_id, error)
