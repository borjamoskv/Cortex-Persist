"""Tests for cortex.memory.ledger — EventLedgerL3.

Tests the immutable event sourcing ledger with a real `:memory:` aiosqlite DB.
Covers: append, replay, count, session retrieval, chain verification.
"""

from __future__ import annotations

import aiosqlite
import pytest

from cortex.memory.ledger import EventLedgerL3
from cortex.memory.models import MemoryEvent

# ─── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
async def ledger():
    """Provide a fresh in-memory ledger per test."""
    conn = await aiosqlite.connect(":memory:")
    ledger_inst = EventLedgerL3(conn)
    await ledger_inst.ensure_table()
    yield ledger_inst
    await conn.close()


def _make_event(
    content: str = "test event",
    role: str = "user",
    tenant_id: str = "test_tenant",
    session_id: str = "sess_1",
    token_count: int = 10,
) -> MemoryEvent:
    """Factory for MemoryEvent with sane defaults."""
    return MemoryEvent(
        role=role,
        content=content,
        token_count=token_count,
        session_id=session_id,
        tenant_id=tenant_id,
    )


# ─── ensure_table ────────────────────────────────────────────────────────


class TestEnsureTable:
    """Ensure table creation is idempotent."""

    @pytest.mark.asyncio
    async def test_idempotent(self, ledger):
        # Second call should be a no-op
        await ledger.ensure_table()

    @pytest.mark.asyncio
    async def test_table_exists_after_init(self, ledger):
        cursor = await ledger._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_events'"
        )
        row = await cursor.fetchone()
        assert row is not None


# ─── append_event ────────────────────────────────────────────────────────


class TestAppendEvent:
    """Tests for immutable event appending."""

    @pytest.mark.asyncio
    async def test_single_append(self, ledger):
        event = _make_event()
        await ledger.append_event(event)
        count = await ledger.count("test_tenant")
        assert count == 1

    @pytest.mark.asyncio
    async def test_signature_generated(self, ledger):
        event = _make_event(content="compute signature")
        await ledger.append_event(event)
        assert event.signature != ""
        assert event.prev_hash == "GENESIS"

    @pytest.mark.asyncio
    async def test_chain_continuation(self, ledger):
        e1 = _make_event(content="first event")
        e2 = _make_event(content="second event")
        await ledger.append_event(e1)
        await ledger.append_event(e2)

        # e2 should chain from e1's signature
        assert e2.prev_hash == e1.signature
        assert e2.signature != e1.signature

    @pytest.mark.asyncio
    async def test_duplicate_event_id_ignored(self, ledger):
        e1 = _make_event()
        await ledger.append_event(e1)
        # Try inserting same event_id again (INSERT OR IGNORE)
        await ledger.append_event(e1)
        count = await ledger.count("test_tenant")
        assert count == 1


# ─── get_session_events ──────────────────────────────────────────────────


class TestGetSessionEvents:
    """Tests for session-scoped retrieval."""

    @pytest.mark.asyncio
    async def test_returns_session_events(self, ledger):
        await ledger.append_event(_make_event(session_id="s1", content="a"))
        await ledger.append_event(_make_event(session_id="s1", content="b"))
        await ledger.append_event(_make_event(session_id="s2", content="c"))

        events = await ledger.get_session_events("s1", tenant_id="test_tenant")
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_empty_session(self, ledger):
        events = await ledger.get_session_events("nonexistent", tenant_id="test_tenant")
        assert events == []

    @pytest.mark.asyncio
    async def test_limit_respected(self, ledger):
        for i in range(10):
            await ledger.append_event(_make_event(content=f"event {i}"))
        events = await ledger.get_session_events("sess_1", tenant_id="test_tenant", limit=3)
        assert len(events) == 3


# ─── replay ──────────────────────────────────────────────────────────────


class TestReplay:
    """Tests for full tenant replay (state reconstruction)."""

    @pytest.mark.asyncio
    async def test_chronological_order(self, ledger):
        await ledger.append_event(_make_event(content="first"))
        await ledger.append_event(_make_event(content="second"))
        await ledger.append_event(_make_event(content="third"))

        events = await ledger.replay("test_tenant")
        contents = [e.content for e in events]
        assert contents == ["first", "second", "third"]

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, ledger):
        await ledger.append_event(_make_event(tenant_id="a", content="for_a"))
        await ledger.append_event(_make_event(tenant_id="b", content="for_b"))

        events_a = await ledger.replay("a")
        events_b = await ledger.replay("b")
        assert len(events_a) == 1
        assert len(events_b) == 1
        assert events_a[0].content == "for_a"


# ─── count ───────────────────────────────────────────────────────────────


class TestCount:
    """Tests for event counting."""

    @pytest.mark.asyncio
    async def test_empty_tenant(self, ledger):
        assert await ledger.count("nonexistent") == 0

    @pytest.mark.asyncio
    async def test_count_by_session(self, ledger):
        await ledger.append_event(_make_event(session_id="s1"))
        await ledger.append_event(_make_event(session_id="s1"))
        await ledger.append_event(_make_event(session_id="s2"))

        assert await ledger.count("test_tenant", session_id="s1") == 2
        assert await ledger.count("test_tenant", session_id="s2") == 1
        assert await ledger.count("test_tenant") == 3


# ─── verify_chain ────────────────────────────────────────────────────────


class TestVerifyChain:
    """Tests for cryptographic chain verification."""

    @pytest.mark.asyncio
    async def test_valid_chain(self, ledger):
        for i in range(5):
            await ledger.append_event(_make_event(content=f"event {i}"))

        result = await ledger.verify_chain("test_tenant")
        assert result["status"] == "VALID"
        assert result["events_audited"] == 5
        assert result["integrity_score"] == 1.0

    @pytest.mark.asyncio
    async def test_empty_chain_valid(self, ledger):
        result = await ledger.verify_chain("empty_tenant")
        assert result["status"] == "VALID"
        assert result["events_audited"] == 0

    @pytest.mark.asyncio
    async def test_tampered_content_detected(self, ledger):
        await ledger.append_event(_make_event(content="original"))

        # Tamper the content directly in DB
        await ledger._conn.execute(
            "UPDATE memory_events SET content = 'tampered' WHERE 1=1"
        )
        await ledger._conn.commit()

        result = await ledger.verify_chain("test_tenant")
        assert result["status"] == "CORRUPT"
        assert result["integrity_score"] < 1.0
        assert any("TAMPER" in f for f in result["findings"])
