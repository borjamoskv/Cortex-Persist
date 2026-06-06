# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""L3 Event Ledger (Immutable Event Sourcing).

Every interaction, thought, and state change is recorded as an immutable
event in SQLite WAL via `cortex.db`. If L1 or L2 collapse, the full
cognitive state can be reconstructed by replaying L3 events.

Uses the hardened `cortex.db.connect_async()` factory for zero-lock I/O.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.memory.models import MemoryEvent

try:
    from cortex.extensions.security.tenant import get_tenant_id
except ImportError:

    def get_tenant_id() -> str:
        return "default"


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
    tenant_id  TEXT NOT NULL DEFAULT 'default',
    prev_hash  TEXT NOT NULL DEFAULT '',
    signature  TEXT NOT NULL DEFAULT '',
    metadata   TEXT NOT NULL DEFAULT '{}'
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_memory_events_session
    ON memory_events(session_id);

CREATE INDEX IF NOT EXISTS idx_memory_events_tenant_event_desc
    ON memory_events(tenant_id, event_id DESC);
"""


class EventLedgerL3:
    """Immutable event sourcing ledger for cognitive memory.

    All writes go through SQLite WAL (via pre-configured aiosqlite
    connection) ensuring non-blocking, crash-safe persistence.
    """

    __slots__ = ("_conn", "_last_hash_cache", "_ready")

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn
        self._ready = False
        self._last_hash_cache: dict[str, str] = {}  # tenant_id -> last_hash

    async def ensure_table(self) -> None:
        """Create the events table if it doesn't exist (idempotent)."""
        if self._ready:
            return
        await self._conn.executescript(_CREATE_TABLE_SQL)
        await self._conn.executescript(_CREATE_INDEX_SQL)
        await self._conn.commit()
        self._ready = True

    async def _get_last_hash(self, tenant_id: str) -> str:
        """Fetch the signature of the last event for a tenant to continue the chain."""
        cursor = await self._conn.execute(
            """SELECT signature FROM memory_events
               WHERE tenant_id = ?
               ORDER BY rowid DESC
               LIMIT 1""",
            (tenant_id,),
        )
        row = await cursor.fetchone()
        last_hash = row[0] if row else "GENESIS"
        self._last_hash_cache[tenant_id] = last_hash
        return last_hash

    async def append_event(self, event: MemoryEvent) -> None:
        """Persist an event immutably. Fire-and-commit with SHA-3-256 integrity."""
        from cortex.engine.causal.taint_engine import enforce_taint_check

        await self.ensure_table()
        token = event.metadata.get("cortex_taint") if event.metadata else None
        await enforce_taint_check(self._conn, token, event.content)

        prev_hash = await self._get_last_hash(event.tenant_id)
        signature = _compute_event_signature(event, prev_hash)
        object.__setattr__(event, "prev_hash", prev_hash)
        object.__setattr__(event, "signature", signature)

        await self._conn.execute(
            """INSERT OR IGNORE INTO memory_events
               (event_id, timestamp, role, content, token_count,
                session_id, tenant_id, prev_hash, signature, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.timestamp.isoformat(),
                event.role,
                event.content,
                event.token_count,
                event.session_id,
                event.tenant_id,
                event.prev_hash,
                event.signature,
                json.dumps(event.metadata),
            ),
        )
        await self._conn.commit()
        self._last_hash_cache[event.tenant_id] = event.signature

    async def get_session_events(
        self,
        session_id: str,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[MemoryEvent]:
        """Retrieve events for a session in chronological order, scoped by tenant."""
        tenant_id = tenant_id or get_tenant_id()
        await self.ensure_table()
        cursor = await self._conn.execute(
            """SELECT event_id, timestamp, role, content, token_count,
                      session_id, tenant_id, prev_hash, signature, metadata
               FROM memory_events
               WHERE session_id = ? AND tenant_id = ?
               ORDER BY rowid ASC
               LIMIT ?""",
            (session_id, tenant_id, limit),
        )
        rows = await cursor.fetchall()
        return [_row_to_event(row) for row in rows]  # type: ignore[reportArgumentType]

    async def replay(self, tenant_id: str, limit: int = 1000) -> list[MemoryEvent]:
        """Replay events for a specific tenant in chronological order for state reconstruction."""
        await self.ensure_table()
        cursor = await self._conn.execute(
            """SELECT event_id, timestamp, role, content, token_count,
                      session_id, tenant_id, prev_hash, signature, metadata
               FROM memory_events
               WHERE tenant_id = ?
               ORDER BY rowid ASC
               LIMIT ?""",
            (tenant_id, limit),
        )
        rows = await cursor.fetchall()
        return [_row_to_event(row) for row in rows]  # type: ignore[reportArgumentType]

    async def count(self, tenant_id: str, session_id: str | None = None) -> int:
        """Count events for a tenant, optionally filtered by session."""
        await self.ensure_table()
        if session_id:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) FROM memory_events WHERE tenant_id = ? AND session_id = ?",
                (tenant_id, session_id),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) FROM memory_events WHERE tenant_id = ?",
                (tenant_id,),
            )
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def verify_chain(self, tenant_id: str) -> dict[str, Any]:
        """
        [GOVERNANCE] Deep cryptographic audit of the memory event chain.
        Recalculates every signature and verifies the back-pointers.
        """
        import hashlib

        await self.ensure_table()
        cursor = await self._conn.execute(
            """SELECT event_id, timestamp, role, content, token_count,
                      session_id, tenant_id, prev_hash, signature, metadata
               FROM memory_events
               WHERE tenant_id = ?
               ORDER BY rowid ASC""",
            (tenant_id,),
        )

        audit_log = []
        is_corrupt = False
        last_sig = "GENESIS"
        count = 0

        async for row in cursor:
            count += 1
            eid, ts, role, content, token_count, session_id, tid, prev_hash, sig, metadata = row

            # 1. Verify Hash Continuity
            if prev_hash != last_sig:
                audit_log.append(
                    f"DISCONTINUITY: Event {eid} expects prev={prev_hash} "
                    f"but actual last={last_sig}"
                )
                is_corrupt = True

            # 2. Verify Signature Integrity
            expected_sig = _compute_event_signature_from_parts(
                event_id=eid,
                timestamp=ts,
                tenant_id=tid,
                role=role,
                content=content,
                token_count=token_count,
                session_id=session_id,
                metadata=json.loads(metadata) if metadata else {},
                prev_hash=prev_hash,
            )

            if sig != expected_sig:
                audit_log.append(
                    f"TAMPER_DETECTED: Event {eid} has sig={sig} "
                    f"but content generates {expected_sig}"
                )
                is_corrupt = True

            last_sig = sig

        integrity = 1.0
        if is_corrupt and count > 0:
            integrity = (count - len(audit_log)) / count

        return {
            "tenant_id": tenant_id,
            "status": "VALID" if not is_corrupt else "CORRUPT",
            "events_audited": count,
            "integrity_score": integrity,
            "findings": audit_log or ["Memory event chain shows 100% integrity."],
            "timestamp": datetime.fromtimestamp(time.monotonic(), tz=timezone.utc).isoformat(),
        }


def _canonical_metadata(metadata: dict[str, Any]) -> str:
    return json.dumps(metadata, sort_keys=True, separators=(",", ":"))


def _compute_event_signature(event: MemoryEvent, prev_hash: str) -> str:
    return _compute_event_signature_from_parts(
        event_id=event.event_id,
        timestamp=event.timestamp.isoformat(),
        tenant_id=event.tenant_id,
        role=event.role,
        content=event.content,
        token_count=event.token_count,
        session_id=event.session_id,
        metadata=event.metadata,
        prev_hash=prev_hash,
    )


def _compute_event_signature_from_parts(
    *,
    event_id: str,
    timestamp: str,
    tenant_id: str,
    role: str,
    content: str,
    token_count: int,
    session_id: str,
    metadata: dict[str, Any],
    prev_hash: str,
) -> str:
    import hashlib

    content_hash = hashlib.sha3_256(content.encode()).hexdigest()
    metadata_hash = hashlib.sha3_256(_canonical_metadata(metadata).encode()).hexdigest()
    payload = (
        f"{event_id}:{timestamp}:{tenant_id}:{role}:{content_hash}:"
        f"{token_count}:{session_id}:{metadata_hash}:{prev_hash}"
    )
    return hashlib.sha3_256(payload.encode()).hexdigest()


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
        tenant_id=row[6],
        prev_hash=row[7],
        signature=row[8],
        metadata=json.loads(row[9]) if row[9] else {},
    )
