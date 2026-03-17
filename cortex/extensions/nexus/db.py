"""
SQLite WAL Backend (Multi-Process Safe)
"""

import json
import os
import sqlite3
import time
from typing import Any, Optional

from cortex.database.core import connect as db_connect
from cortex.extensions.nexus.types import DomainOrigin, IntentType, WorldMutation


class NexusDB:
    """Thin SQLite WAL wrapper for cross-process mutation persistence.

    Every process (MailTV daemon, Moltbook agent, CORTEX core) can read/write
    to the same database concurrently without locks.
    """

    __slots__ = ("_db_path",)

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = db_connect(
            self._db_path,
            timeout=10,
            row_factory=sqlite3.Row,
        )
        return conn

    def _init_schema(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nexus_mutations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idempotency_key TEXT UNIQUE NOT NULL,
                origin TEXT NOT NULL,
                intent TEXT NOT NULL,
                project TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 1.0,
                priority INTEGER NOT NULL DEFAULT 2,
                timestamp REAL NOT NULL,
                created_at REAL NOT NULL DEFAULT (unixepoch('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_nexus_origin
                ON nexus_mutations(origin);
            CREATE INDEX IF NOT EXISTS idx_nexus_intent
                ON nexus_mutations(intent);
            CREATE INDEX IF NOT EXISTS idx_nexus_project
                ON nexus_mutations(project);
            CREATE INDEX IF NOT EXISTS idx_nexus_timestamp
                ON nexus_mutations(timestamp);
            CREATE INDEX IF NOT EXISTS idx_nexus_priority
                ON nexus_mutations(priority);
        """)
        conn.commit()
        conn.close()

    def insert(self, mutation: WorldMutation) -> bool:
        """Insert a mutation. Returns False if deduplicated (already exists)."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO nexus_mutations
                   (idempotency_key, origin, intent, project, payload_json,
                    confidence, priority, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    mutation.idempotency_key,
                    mutation.origin.name,
                    mutation.intent.name,
                    mutation.project,
                    json.dumps(mutation.payload, default=str),
                    mutation.confidence,
                    mutation.priority.value,
                    mutation.timestamp,
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate idempotency_key → already processed
            return False
        finally:
            conn.close()

    def query(
        self,
        origin: Optional[DomainOrigin] = None,
        intent: Optional[IntentType] = None,
        project: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query the World Model. All filters are optional."""
        conn = self._get_conn()
        clauses: list[str] = []
        params: list[Any] = []

        if origin:
            clauses.append("origin = ?")
            params.append(origin.name)
        if intent:
            clauses.append("intent = ?")
            params.append(intent.name)
        if project:
            clauses.append("project = ?")
            params.append(project)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        rows = conn.execute(
            f"SELECT * FROM nexus_mutations {where} ORDER BY priority ASC, timestamp DESC LIMIT ?",
            params,
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def count(self) -> int:
        conn = self._get_conn()
        n = conn.execute("SELECT COUNT(*) FROM nexus_mutations").fetchone()[0]
        conn.close()
        return n

    def purge_old(self, older_than: Optional[float] = None) -> int:
        """Remove mutations older than a timestamp. Returns count deleted."""
        cutoff = older_than or (time.time() - 86400 * 7)  # Default: 7 days
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM nexus_mutations WHERE timestamp < ?", (cutoff,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        return deleted
