# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - Message Bus.

MessageBus protocol and SQLite implementation wrapping the
existing AtomicMailbox with typed AgentMessage serialization.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Protocol

from cortex.agents.message_schema import AgentMessage
from cortex.database.core import connect_async, causal_write

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
    Wraps the transport layer - does NOT reuse AtomicMailbox
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
            async with self._lock:
                if self._conn is None:
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
            with causal_write(conn):
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
            with causal_write(conn):
                # Atomic update with RETURNING clause to prevent multi-process race conditions
                async with conn.execute(
                    "UPDATE agent_messages SET consumed = 1 "
                    "WHERE id = (SELECT id FROM agent_messages WHERE recipient = ? AND consumed = 0 ORDER BY id ASC LIMIT 1) "
                    "RETURNING id, payload",
                    (agent_id,),
                ) as cursor:
                    row = await cursor.fetchone()

                if row is None:
                    return None

                row_id, raw_payload = row
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
        conn = await self._get_conn()
        async with self._lock:
            with causal_write(conn):
                await conn.execute(
                    "INSERT INTO agent_messages (recipient, payload, created_at) VALUES (?, ?, ?)",
                    ("*", message.to_json(), message.created_at),
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

    async def purge_consumed(self) -> int:
        """Remove all consumed messages from the bus."""
        conn = await self._get_conn()
        deleted = 0
        async with self._lock:
            with causal_write(conn):
                async with conn.execute("DELETE FROM agent_messages WHERE consumed = 1") as cursor:
                    deleted = cursor.rowcount
                await conn.commit()
        return deleted

    async def close(self) -> None:
        """Close the bus connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None


class ByzantineZeroCopyBus:
    """Zero-copy MessageBus implementation for Byzantine Swarms (C5-REAL).

    Uses cortex_rs.ZeroCopyRingBuffer for O(1) Exergy message passing,
    and HMAC-SHA256 signatures to reject Byzantine faults and forged messages.
    """

    def __init__(
        self, bin_path: str = "cortex_swarm.bin", capacity: int = 10000, secret: str | None = None
    ):
        """Initialize Byzantine bus.

        Args:
            secret: HMAC signing key. Defaults to CORTEX_BUS_SECRET env var,
                    or a random 32-byte key if neither is provided.
                    WARNING: In production multi-process deployments, set
                    CORTEX_BUS_SECRET explicitly so all processes share a key.
        """
        self.bin_path = bin_path
        # Late import to prevent circular dependency
        import cortex_rs

        self.ring = cortex_rs.ZeroCopyRingBuffer(self.bin_path, capacity)
        resolved_secret = secret or os.environ.get("CORTEX_BUS_SECRET") or os.urandom(32).hex()
        self.secret = resolved_secret.encode("utf-8")
        self._lock = asyncio.Lock()

    def _sign(self, msg_json: str) -> str:
        import hashlib
        import hmac

        return hmac.new(self.secret, msg_json.encode("utf-8"), hashlib.sha256).hexdigest()

    async def send(self, message: AgentMessage) -> None:
        """Enqueue a message with Byzantine signature."""
        msg_json = message.to_json()
        sig = self._sign(msg_json)

        # Format: <sig_64_bytes>:<msg_json>
        payload_str = f"{sig}:{msg_json}"
        payload_bytes = payload_str.encode("utf-8")

        if len(payload_bytes) > 4023:
            raise ValueError(
                f"Message payload too large for ZeroCopyRingBuffer: {len(payload_bytes)} > 4023 bytes"
            )

        async with self._lock:
            # Enqueue returns True if successful
            success = self.ring.enqueue(message.recipient.encode("utf-8"), payload_bytes)
            if not success:
                logger.error("ByzantineZeroCopyBus: Ring buffer is full!")

        logger.debug(
            "ZeroCopyBus: %s → %s [%s]",
            message.sender,
            message.recipient,
            message.kind.value,
        )

    async def receive(self, agent_id: str, timeout: float = 1.0) -> AgentMessage | None:
        """Polls the zero-copy ring buffer for messages."""
        start = time.monotonic()
        while True:
            # fetch_pending returns list of tuples: (index, timestamp, agent_id_bytes, payload_bytes)
            # It also transitions the status to 'processing' in memory.
            # In a real distributed system, we'd need acking, but for this C5-REAL local swarm,
            # fetch_pending removes it from the pending queue (sets to processing/0).
            pending = self.ring.fetch_pending()

            for _idx, _ts, rec_id, payload_bytes in pending:
                try:
                    rec_str = rec_id.decode("utf-8").strip("\x00")
                    if rec_str == agent_id or rec_str == "*":
                        payload_str = payload_bytes.decode("utf-8").strip("\x00")
                        if ":" not in payload_str:
                            continue

                        sig, msg_json = payload_str.split(":", 1)
                        expected_sig = self._sign(msg_json)
                        if sig != expected_sig:
                            logger.error(
                                "Byzantine Fault Detected: Forged message signature rejected! %s != %s",
                                sig,
                                expected_sig,
                            )
                            continue

                        return AgentMessage.from_json(msg_json)
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning("ZeroCopyBus: Failed to deserialize message: %s", e)

            if timeout <= 0 or (time.monotonic() - start) >= timeout:
                break
            await asyncio.sleep(0.01)

        return None

    async def broadcast(self, message: AgentMessage) -> None:
        message.recipient = "*"
        await self.send(message)

    async def close(self) -> None:
        pass
