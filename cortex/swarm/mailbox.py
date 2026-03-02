"""CORTEX V5 - Atomic Mailbox (LEGION-Ω)
Zero-latency inter-agent communication via SQLite.
Eliminates the coordinator by allowing agents to read/write
asynchronously to an atomic embedded database.
"""

from __future__ import annotations

import json
from typing import Any

from cortex.database.core import connect_async


class AtomicMailbox:
    """O(1) SQLite atomic mailbox for Swarm zero-latency communication.
    Refactored to be ASYNC to prevent Event Loop Starvation.
    """

    def __init__(self, db_path: str = "file::memory:?cache=shared") -> None:
        self.db_path = db_path
        self._conn = None

    async def _get_conn(self):
        """Lazy load async connection."""
        if self._conn is None:
            self._conn = await connect_async(self.db_path)
            # Ensure table exists
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON messages(topic);")
            await self._conn.commit()
        return self._conn

    async def post(self, topic: str, agent_id: str, payload: dict[str, Any] | str) -> None:
        """Atomic write to the mailbox without waiting for a coordinator."""
        if isinstance(payload, dict):
            payload = json.dumps(payload)

        conn = await self._get_conn()
        await conn.execute(
            "INSERT INTO messages (topic, agent_id, payload) VALUES (?, ?, ?)",
            (topic, agent_id, payload),
        )
        await conn.commit()

    async def read(self, topic: str) -> list[tuple[str, str, str]]:
        """O(1) read all messages for a topic."""
        conn = await self._get_conn()
        async with conn.execute(
            """
            SELECT agent_id, payload, timestamp FROM messages
            WHERE topic = ? ORDER BY id ASC
            """,
            (topic,),
        ) as cursor:
            return await cursor.fetchall()

    async def clear(self, topic: str) -> None:
        """Clear topic messages."""
        conn = await self._get_conn()
        await conn.execute("DELETE FROM messages WHERE topic = ?", (topic,))
        await conn.commit()

    async def close(self) -> None:
        """Close the mailbox connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
