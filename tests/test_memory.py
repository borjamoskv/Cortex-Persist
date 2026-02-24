# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.3 — Cognitive Memory Tests.

Tests for the Tripartite Memory Architecture (KETER-∞ Frontera 2):
- L1: WorkingMemoryL1 (token-budgeted sliding window)
- L3: EventLedgerL3 (SQLite WAL immutable event log)
- Orchestrator: CortexMemoryManager (L1 → L2 → L3)
"""

from __future__ import annotations

import aiosqlite
import pytest

from cortex.memory.ledger import EventLedgerL3
from cortex.memory.models import EpisodicSnapshot, MemoryEvent
from cortex.memory.working import WorkingMemoryL1

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def l1():
    """Working memory with a small budget for testing overflow."""
    return WorkingMemoryL1(max_tokens=100)


@pytest.fixture
def make_event():
    """Factory for creating test MemoryEvents."""

    def _make(
        role: str = "user",
        content: str = "test content",
        token_count: int = 25,
        session_id: str = "test-session",
    ) -> MemoryEvent:
        return MemoryEvent(
            role=role,
            content=content,
            token_count=token_count,
            session_id=session_id,
        )

    return _make


@pytest.fixture
async def ledger(tmp_path):
    """L3 Event Ledger backed by a temp SQLite database."""
    db_path = str(tmp_path / "test_ledger.db")
    conn = await aiosqlite.connect(db_path)
    # Apply pragmas manually (test isolation)
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA busy_timeout=5000")
    await conn.commit()

    led = EventLedgerL3(conn)
    yield led

    await conn.close()


# ─── L1: Working Memory Tests ────────────────────────────────────────


class TestWorkingMemoryL1:
    def test_add_within_budget(self, l1, make_event):
        """Events within budget produce no overflow."""
        event = make_event(token_count=50)
        overflow = l1.add_event(event)
        assert overflow == []
        assert l1.event_count == 1
        assert l1.current_tokens == 50

    def test_overflow_evicts_oldest(self, l1, make_event):
        """When budget is exceeded, oldest events are evicted FIFO."""
        e1 = make_event(content="first", token_count=60)
        e2 = make_event(content="second", token_count=60)

        overflow1 = l1.add_event(e1)
        assert overflow1 == []

        overflow2 = l1.add_event(e2)
        assert len(overflow2) == 1
        assert overflow2[0].content == "first"
        assert l1.event_count == 1
        assert l1.current_tokens == 60

    def test_multiple_evictions(self, l1, make_event):
        """A single large event can evict multiple small ones."""
        small = [make_event(content=f"s{i}", token_count=20) for i in range(5)]
        for s in small:
            l1.add_event(s)
        assert l1.event_count == 5
        assert l1.current_tokens == 100

        # Add a big event that forces evicting multiple
        big = make_event(content="big", token_count=80)
        overflow = l1.add_event(big)
        assert len(overflow) >= 4  # Need to free at least 80 tokens
        assert l1.current_tokens <= 100

    def test_get_context(self, l1, make_event):
        """get_context returns prompt-ready message dicts."""
        l1.add_event(make_event(role="user", content="hello"))
        l1.add_event(make_event(role="assistant", content="world"))

        ctx = l1.get_context()
        assert len(ctx) == 2
        assert ctx[0] == {"role": "user", "content": "hello"}
        assert ctx[1] == {"role": "assistant", "content": "world"}

    def test_clear_returns_buffer(self, l1, make_event):
        """clear() returns all events and resets state."""
        l1.add_event(make_event(token_count=30))
        l1.add_event(make_event(token_count=40))

        flushed = l1.clear()
        assert len(flushed) == 2
        assert l1.event_count == 0
        assert l1.current_tokens == 0

    def test_utilization(self, l1, make_event):
        """utilization reports correct token ratio."""
        l1.add_event(make_event(token_count=50))
        assert l1.utilization == pytest.approx(0.5)

    def test_zero_max_tokens_raises(self):
        """max_tokens <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            WorkingMemoryL1(max_tokens=0)

    def test_repr(self, l1, make_event):
        """repr is informative."""
        l1.add_event(make_event(token_count=50))
        r = repr(l1)
        assert "events=1" in r
        assert "50/100" in r


# ─── L3: Event Ledger Tests ──────────────────────────────────────────


class TestEventLedgerL3:
    @pytest.mark.asyncio
    async def test_append_and_retrieve(self, ledger, make_event):
        """Events can be appended and retrieved by session."""
        event = make_event(session_id="s1", content="decision made")
        await ledger.append_event(event)

        events = await ledger.get_session_events("s1")
        assert len(events) == 1
        assert events[0].content == "decision made"
        assert events[0].event_id == event.event_id

    @pytest.mark.asyncio
    async def test_replay_chronological(self, ledger, make_event):
        """replay() returns all events in chronological order."""
        e1 = make_event(session_id="s1", content="first")
        e2 = make_event(session_id="s1", content="second")
        await ledger.append_event(e1)
        await ledger.append_event(e2)

        all_events = await ledger.replay()
        assert len(all_events) == 2
        assert all_events[0].content == "first"
        assert all_events[1].content == "second"

    @pytest.mark.asyncio
    async def test_count(self, ledger, make_event):
        """count() reports correct totals."""
        await ledger.append_event(make_event(session_id="s1"))
        await ledger.append_event(make_event(session_id="s2"))

        assert await ledger.count() == 2
        assert await ledger.count(session_id="s1") == 1

    @pytest.mark.asyncio
    async def test_idempotent_append(self, ledger, make_event):
        """Duplicate event_id is silently ignored (INSERT OR IGNORE)."""
        event = make_event(session_id="s1")
        await ledger.append_event(event)
        await ledger.append_event(event)  # Same event_id

        assert await ledger.count() == 1

    @pytest.mark.asyncio
    async def test_session_isolation(self, ledger, make_event):
        """Events from different sessions don't leak."""
        await ledger.append_event(make_event(session_id="s1", content="a"))
        await ledger.append_event(make_event(session_id="s2", content="b"))

        s1_events = await ledger.get_session_events("s1")
        assert len(s1_events) == 1
        assert s1_events[0].content == "a"


# ─── Models Tests ────────────────────────────────────────────────────


class TestModels:
    def test_memory_event_defaults(self):
        """MemoryEvent auto-generates id and timestamp."""
        event = MemoryEvent(
            role="user",
            content="test",
            token_count=10,
            session_id="s1",
        )
        assert event.event_id  # UUID generated
        assert event.timestamp  # Timestamp generated
        assert event.metadata == {}

    def test_episodic_snapshot_defaults(self):
        """EpisodicSnapshot auto-generates id and timestamp."""
        snap = EpisodicSnapshot(
            summary="Discussed architecture",
            vector_embedding=[0.1] * 384,
        )
        assert snap.snapshot_id
        assert snap.created_at
        assert snap.linked_events == []
        assert snap.session_id == ""

    def test_memory_event_validation(self):
        """token_count must be >= 0."""
        with pytest.raises(ValueError):  # Pydantic ValidationError
            MemoryEvent(
                role="user",
                content="test",
                token_count=-1,
                session_id="s1",
            )
