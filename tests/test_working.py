"""Tests for cortex.memory.working — L1 Working Memory (Sliding Window)."""

from __future__ import annotations

import pytest

# Stub qdrant_client before importing cortex.memory (import chain:
# cortex.memory.__init__ → manager → vector_store → qdrant_client)
import sys
from unittest.mock import MagicMock

_qd = MagicMock()
sys.modules["qdrant_client"] = _qd
sys.modules["qdrant_client.models"] = _qd.models

from cortex.memory.models import MemoryEvent  # noqa: E402
from cortex.memory.working import DEFAULT_MAX_TOKENS, WorkingMemoryL1


# ─── Helpers ──────────────────────────────────────────────────────────


def _event(content: str = "test", tokens: int = 100, role: str = "user") -> MemoryEvent:
    """Create a minimal MemoryEvent for testing."""
    return MemoryEvent(
        role=role,
        content=content,
        token_count=tokens,
        session_id="test-session",
    )


# ─── Construction ─────────────────────────────────────────────────────


class TestConstruction:
    def test_default_max_tokens(self):
        l1 = WorkingMemoryL1()
        assert l1.max_tokens == DEFAULT_MAX_TOKENS

    def test_custom_max_tokens(self):
        l1 = WorkingMemoryL1(max_tokens=1024)
        assert l1.max_tokens == 1024

    def test_zero_max_tokens_raises(self):
        with pytest.raises(ValueError, match="positive"):
            WorkingMemoryL1(max_tokens=0)

    def test_negative_max_tokens_raises(self):
        with pytest.raises(ValueError, match="positive"):
            WorkingMemoryL1(max_tokens=-1)

    def test_starts_empty(self):
        l1 = WorkingMemoryL1()
        assert l1.current_tokens == 0
        assert l1.event_count == 0
        assert len(l1) == 0


# ─── Add Event ────────────────────────────────────────────────────────


class TestAddEvent:
    def test_add_single_event(self):
        l1 = WorkingMemoryL1(max_tokens=500)
        overflow = l1.add_event(_event(tokens=100))
        assert overflow == []
        assert l1.event_count == 1
        assert l1.current_tokens == 100

    def test_add_multiple_events_no_overflow(self):
        l1 = WorkingMemoryL1(max_tokens=500)
        l1.add_event(_event(tokens=100))
        l1.add_event(_event(tokens=200))
        assert l1.event_count == 2
        assert l1.current_tokens == 300

    def test_overflow_evicts_oldest(self):
        l1 = WorkingMemoryL1(max_tokens=250)
        l1.add_event(_event("first", tokens=100))
        l1.add_event(_event("second", tokens=100))
        overflow = l1.add_event(_event("third", tokens=100))

        assert len(overflow) == 1
        assert overflow[0].content == "first"
        assert l1.event_count == 2
        assert l1.current_tokens == 200

    def test_large_event_evicts_multiple(self):
        l1 = WorkingMemoryL1(max_tokens=300)
        l1.add_event(_event("a", tokens=100))
        l1.add_event(_event("b", tokens=100))
        l1.add_event(_event("c", tokens=100))

        # This big event should evict all previous ones
        overflow = l1.add_event(_event("big", tokens=250))

        assert len(overflow) == 3
        assert l1.event_count == 1
        assert l1.current_tokens == 250

    def test_overflow_preserves_order(self):
        l1 = WorkingMemoryL1(max_tokens=200)
        l1.add_event(_event("a", tokens=100))
        l1.add_event(_event("b", tokens=100))
        overflow = l1.add_event(_event("c", tokens=100))

        assert overflow[0].content == "a"
        context = l1.get_context()
        assert context[0]["content"] == "b"
        assert context[1]["content"] == "c"


# ─── Get Context ──────────────────────────────────────────────────────


class TestGetContext:
    def test_empty_context(self):
        l1 = WorkingMemoryL1()
        assert l1.get_context() == []

    def test_context_format(self):
        l1 = WorkingMemoryL1()
        l1.add_event(_event("hello", role="user"))
        l1.add_event(_event("world", role="assistant"))

        ctx = l1.get_context()
        assert len(ctx) == 2
        assert ctx[0] == {"role": "user", "content": "hello"}
        assert ctx[1] == {"role": "assistant", "content": "world"}


# ─── Clear ────────────────────────────────────────────────────────────


class TestClear:
    def test_clear_returns_events(self):
        l1 = WorkingMemoryL1()
        l1.add_event(_event("a", tokens=50))
        l1.add_event(_event("b", tokens=50))

        flushed = l1.clear()
        assert len(flushed) == 2
        assert flushed[0].content == "a"

    def test_clear_resets_state(self):
        l1 = WorkingMemoryL1()
        l1.add_event(_event(tokens=100))
        l1.clear()

        assert l1.event_count == 0
        assert l1.current_tokens == 0
        assert l1.get_context() == []

    def test_clear_empty_buffer(self):
        l1 = WorkingMemoryL1()
        flushed = l1.clear()
        assert flushed == []


# ─── Introspection ────────────────────────────────────────────────────


class TestIntrospection:
    def test_utilization_empty(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        assert l1.utilization == 0.0

    def test_utilization_partial(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        l1.add_event(_event(tokens=500))
        assert l1.utilization == pytest.approx(0.5)

    def test_utilization_full(self):
        l1 = WorkingMemoryL1(max_tokens=100)
        l1.add_event(_event(tokens=100))
        assert l1.utilization == pytest.approx(1.0)

    def test_repr(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        l1.add_event(_event(tokens=250))
        r = repr(l1)
        assert "events=1" in r
        assert "tokens=250/1000" in r
        assert "25.0%" in r

    def test_len_matches_event_count(self):
        l1 = WorkingMemoryL1()
        l1.add_event(_event(tokens=10))
        l1.add_event(_event(tokens=20))
        assert len(l1) == l1.event_count == 2
