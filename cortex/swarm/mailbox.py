"""CORTEX V5 - Atomic Mailbox (LEGION-Ω)
Zero-latency inter-agent communication via SQLite.
Eliminates the coordinator by allowing agents to read/write
asynchronously to an atomic embedded database.
"""

from __future__ import annotations

import json
from typing import Any

from cortex.database.core import connect as db_connect


class AtomicMailbox:
    """O(1) SQLite atomic mailbox for Swarm zero-latency communication."""

    def __init__(self, db_path: str = "file::memory:?cache=shared") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with db_connect(self.db_path, uri=True) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON messages(topic);")

    def post(self, topic: str, agent_id: str, payload: dict[str, Any] | str) -> None:
        """Atomic write to the mailbox without waiting for a coordinator."""
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        with db_connect(self.db_path, uri=True) as conn:
            conn.execute(
                "INSERT INTO messages (topic, agent_id, payload) VALUES (?, ?, ?)",
                (topic, agent_id, payload)
            )

    def read(self, topic: str) -> list[tuple[str, str, str]]:
        """O(1) read all messages for a topic."""
        with db_connect(self.db_path, uri=True) as conn:
            cursor = conn.execute(
                """
                SELECT agent_id, payload, timestamp FROM messages
                WHERE topic = ? ORDER BY timestamp ASC
                """,
                (topic,),
            )
            return cursor.fetchall()

    def clear(self, topic: str) -> None:
        """Clear topic messages."""
        with db_connect(self.db_path, uri=True) as conn:
            conn.execute("DELETE FROM messages WHERE topic = ?", (topic,))
