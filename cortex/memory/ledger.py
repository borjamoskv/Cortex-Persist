# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.3 — L3 Event Ledger (Immutable Event Sourcing).

Every interaction, thought, and state change is recorded as an immutable
event in SQLite WAL via `cortex.db`. If L1 or L2 collapse, the full
cognitive state can be reconstructed by replaying L3 events.

Uses the hardened `cortex.db.connect_async()` factory for zero-lock I/O.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import aiosqlite

from cortex.memory.models import MemoryEvent

__all__ = ["EventLedgerL3"]

logger = logging.getLogger("cortex.memory.ledger")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS memory_events (
    event_id   TEXT PRIMARY KEY,
    timestamp  TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    session_id TEXT NOT NULL,
    metadata   TEXT NOT NULL DEFAULT '{}'
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_memory_events_session
    ON memory_events(session_id);
"""


class EventLedgerL3:
    """Immutable event sourcing ledger for cognitive memory.

    All writes go through SQLite WAL (via pre-configured aiosqlite
    connection) ensuring non-blocking, crash-safe persistence.

    Args:
        conn: An aiosqlite connection (from `cortex.db.connect_async()`).
    """

    __slots__ = ("_conn", "_ready")

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn
        self._ready = False

    async def ensure_table(self) -> None:
        """Create the events table if it doesn't exist (idempotent)."""
        if self._ready:
            return
        await self._conn.execute(_CREATE_TABLE_SQL)
        await self._conn.execute(_CREATE_INDEX_SQL)
        await self._conn.commit()
        self._ready = True

    async def append_event(self, event: MemoryEvent) -> None:
        """Persist an event immutably. Fire-and-commit."""
        await self.ensure_table()
        await self._conn.execute(
            """INSERT OR IGNORE INTO memory_events
               (event_id, timestamp, role, content, token_count, session_id, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.timestamp.isoformat(),
                event.role,
                event.content,
                event.token_count,
                event.session_id,
                json.dumps(event.metadata),
            ),
        )
        await self._conn.commit()

    async def get_session_events(
        self,
        session_id: str,
        limit: int = 100,
    ) -> list[MemoryEvent]:
        """Retrieve events for a session in chronological order."""
        await self.ensure_table()
        cursor = await self._conn.execute(
            """SELECT event_id, timestamp, role, content, token_count, session_id, metadata
               FROM memory_events
               WHERE session_id = ?
               ORDER BY timestamp ASC
               LIMIT ?""",
            (session_id, limit),
        )
        rows = await cursor.fetchall()
        return [_row_to_event(row) for row in rows]

    async def replay(self, limit: int = 1000) -> list[MemoryEvent]:
        """Replay all events in chronological order for state reconstruction."""
        await self.ensure_table()
        cursor = await self._conn.execute(
            """SELECT event_id, timestamp, role, content, token_count, session_id, metadata
               FROM memory_events
               ORDER BY timestamp ASC
               LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [_row_to_event(row) for row in rows]

    async def count(self, session_id: str | None = None) -> int:
        """Count events, optionally filtered by session."""
        await self.ensure_table()
        if session_id:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) FROM memory_events WHERE session_id = ?",
                (session_id,),
            )
        else:
            cursor = await self._conn.execute("SELECT COUNT(*) FROM memory_events")
        row = await cursor.fetchone()
        return row[0] if row else 0


def _row_to_event(row: tuple) -> MemoryEvent:
    """Convert a database row to a MemoryEvent model."""
    raw_ts = row[1]
    ts = datetime.fromisoformat(raw_ts) if isinstance(raw_ts, str) else raw_ts
    return MemoryEvent(
        event_id=row[0],
        timestamp=ts,
        role=row[2],
        content=row[3],
        token_count=row[4],
        session_id=row[5],
        metadata=json.loads(row[6]) if row[6] else {},
    )
