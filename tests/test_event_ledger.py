# fmt: off
"""
CORTEX v5.3 — Event Ledger (L3) Tests.

Tests for EventLedgerL3: immutable event sourcing via SQLite WAL.
Uses a temporary in-memory database for test isolation.
"""
# fmt: on

from __future__ import annotations

import aiosqlite
import pytest

from cortex.memory.ledger import EventLedgerL3
from cortex.memory.models import MemoryEvent


# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
async def ledger():
    """L3 Ledger backed by a disposable in-memory SQLite DB."""
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA busy_timeout=5000")
    ledger = EventLedgerL3(conn)
    await ledger.ensure_table()
    yield ledger
    await conn.close()


def _event(
    content: str = "test",
    session_id: str = "sess-1",
    role: str = "user",
    tokens: int = 50,
) -> MemoryEvent:
    """Quick MemoryEvent factory."""
    return MemoryEvent(
        role=role,
        content=content,
        token_count=tokens,
        session_id=session_id,
    )


# ─── Core Behavior ───────────────────────────────────────────────────


class TestEventLedgerL3:
    async def test_append_and_retrieve(self, ledger):
        """Basic write and read cycle."""
        event = _event("SQLite WAL is fast")
        await ledger.append_event(event)

        events = await ledger.get_session_events("sess-1")
        assert len(events) == 1
        assert events[0].content == "SQLite WAL is fast"
        assert events[0].event_id == event.event_id

    async def test_append_is_idempotent(self, ledger):
        """Inserting the same event_id twice should not duplicate."""
        event = _event("deduplicated")
        await ledger.append_event(event)
        await ledger.append_event(event)  # INSERT OR IGNORE

        count = await ledger.count()
        assert count == 1

    async def test_session_filter(self, ledger):
        """get_session_events should filter by session_id."""
        await ledger.append_event(_event("a", session_id="sess-1"))
        await ledger.append_event(_event("b", session_id="sess-2"))
        await ledger.append_event(_event("c", session_id="sess-1"))

        events = await ledger.get_session_events("sess-1")
        assert len(events) == 2
        assert all(e.session_id == "sess-1" for e in events)

    async def test_replay_all(self, ledger):
        """replay() should return all events chronologically."""
        await ledger.append_event(_event("first", session_id="s1"))
        await ledger.append_event(_event("second", session_id="s2"))
        await ledger.append_event(_event("third", session_id="s1"))

        events = await ledger.replay()
        assert len(events) == 3

    async def test_count_all(self, ledger):
        """count() without session filter returns total."""
        await ledger.append_event(_event("a", session_id="s1"))
        await ledger.append_event(_event("b", session_id="s2"))

        assert await ledger.count() == 2

    async def test_count_by_session(self, ledger):
        """count(session_id) returns per-session count."""
        await ledger.append_event(_event("a", session_id="s1"))
        await ledger.append_event(_event("b", session_id="s1"))
        await ledger.append_event(_event("c", session_id="s2"))

        assert await ledger.count("s1") == 2
        assert await ledger.count("s2") == 1

    async def test_ensure_table_idempotent(self, ledger):
        """Calling ensure_table multiple times should not error."""
        await ledger.ensure_table()
        await ledger.ensure_table()
        assert await ledger.count() == 0

    async def test_metadata_preserved(self, ledger):
        """Event metadata should survive the SQLite roundtrip."""
        event = _event("with meta")
        event.metadata = {"tool": "qdrant", "version": 3}
        await ledger.append_event(event)

        events = await ledger.get_session_events("sess-1")
        assert events[0].metadata["tool"] == "qdrant"
        assert events[0].metadata["version"] == 3

    async def test_empty_ledger(self, ledger):
        """Operations on empty ledger should return safe defaults."""
        assert await ledger.count() == 0
        assert await ledger.get_session_events("nonexistent") == []
        assert await ledger.replay() == []
