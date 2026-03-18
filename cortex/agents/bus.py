"""CORTEX Agent Runtime — Message Bus.

MessageBus protocol and SQLite implementation wrapping the
existing AtomicMailbox with typed AgentMessage serialization.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Protocol

from cortex.agents.message_schema import AgentMessage

logger = logging.getLogger("cortex.agents.bus")


class MessageBus(Protocol):
    """Protocol for inter-agent message transport."""

    async def send(self, message: AgentMessage) -> None: ...
    async def receive(self, agent_id: str, timeout: float = 1.0) -> AgentMessage | None: ...
    async def broadcast(self, message: AgentMessage) -> None: ...
    async def close(self) -> None: ...


class SqliteMessageBus:
    """SQLite-backed message bus using aiosqlite.

    Uses a simple queue table with agent_id routing.
    Wraps the transport layer — does NOT reuse AtomicMailbox
    directly because we need typed AgentMessage serialization
    and per-recipient queuing (not topic-based).
    """

    def __init__(self, db_path: str = "file::memory:?cache=shared") -> None:
        self.db_path = db_path
        self._conn: Any = None
        self._lock = asyncio.Lock()

    async def _get_conn(self) -> Any:
        """Lazy-init async connection."""
        if self._conn is None:
            from cortex.database.core import connect_async

            self._conn = await connect_async(self.db_path)
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    consumed INTEGER DEFAULT 0
                )
            """)
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_msg_recipient "
                "ON agent_messages(recipient, consumed)"
            )
            await self._conn.commit()
        return self._conn

    async def send(self, message: AgentMessage) -> None:
        """Enqueue a message for a specific recipient."""
        conn = await self._get_conn()
        async with self._lock:
            await conn.execute(
                "INSERT INTO agent_messages (recipient, payload, created_at) VALUES (?, ?, ?)",
                (message.recipient, message.to_json(), message.created_at),
            )
            await conn.commit()
        logger.debug(
            "Bus: %s → %s [%s]",
            message.sender,
            message.recipient,
            message.kind.value,
        )

    async def receive(self, agent_id: str, timeout: float = 1.0) -> AgentMessage | None:
        """Dequeue the oldest unconsumed message for agent_id.

        Polls once. If no message, waits up to timeout then returns None.
        """
        conn = await self._get_conn()

        # Try immediate fetch
        msg = await self._fetch_one(conn, agent_id)
        if msg is not None:
            return msg

        # Wait and retry once
        if timeout > 0:
            await asyncio.sleep(min(timeout, 1.0))
            return await self._fetch_one(conn, agent_id)

        return None

    async def _fetch_one(self, conn: Any, agent_id: str) -> AgentMessage | None:
        """Fetch and consume one message atomically."""
        row = None
        async with self._lock:
            async with conn.execute(
                "SELECT id, payload FROM agent_messages "
                "WHERE recipient = ? AND consumed = 0 "
                "ORDER BY id ASC LIMIT 1",
                (agent_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if row is None:
                return None

            row_id, raw_payload = row
            await conn.execute(
                "UPDATE agent_messages SET consumed = 1 WHERE id = ?",
                (row_id,),
            )
            await conn.commit()

        try:
            return AgentMessage.from_json(raw_payload)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Bus: Failed to deserialize message %d: %s", row_id, exc)
            return None

    async def broadcast(self, message: AgentMessage) -> None:
        """Send a message to all agents (recipient='*').

        Note: broadcast messages are stored with recipient='*'.
        Agents must explicitly poll for broadcast messages.
        """
        broadcast_msg = AgentMessage(
            message_id=message.message_id,
            sender=message.sender,
            recipient="*",
            kind=message.kind,
            payload=message.payload,
            created_at=message.created_at,
            correlation_id=message.correlation_id,
        )
        conn = await self._get_conn()
        async with self._lock:
            await conn.execute(
                "INSERT INTO agent_messages (recipient, payload, created_at) VALUES (?, ?, ?)",
                ("*", broadcast_msg.to_json(), broadcast_msg.created_at),
            )
            await conn.commit()

    async def pending_count(self, agent_id: str) -> int:
        """Count unconsumed messages for an agent."""
        conn = await self._get_conn()
        async with conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE recipient = ? AND consumed = 0",
            (agent_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def purge_consumed(self, older_than_seconds: float = 3600) -> int:
        """Delete consumed messages older than threshold."""
        conn = await self._get_conn()
        cutoff = time.time() - older_than_seconds
        async with self._lock:
            cursor = await conn.execute(
                "DELETE FROM agent_messages WHERE consumed = 1 AND created_at < ?",
                (cutoff,),
            )
            await conn.commit()
            return cursor.rowcount

    async def close(self) -> None:
        """Close the bus connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
