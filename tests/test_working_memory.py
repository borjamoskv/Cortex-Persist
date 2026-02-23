# fmt: off
"""
CORTEX v5.3 — Working Memory (L1) Tests.

Tests for WorkingMemoryL1: FIFO sliding window with token-budgeted eviction.
"""
# fmt: on

from __future__ import annotations

import pytest

from cortex.memory.models import MemoryEvent
from cortex.memory.working import DEFAULT_MAX_TOKENS, WorkingMemoryL1


# ─── Helpers ──────────────────────────────────────────────────────────


def _event(content: str = "test", tokens: int = 100, role: str = "user") -> MemoryEvent:
    """Quick MemoryEvent factory."""
    return MemoryEvent(
        role=role,
        content=content,
        token_count=tokens,
        session_id="test-session",
    )


# ─── Core Behavior ───────────────────────────────────────────────────


class TestWorkingMemoryL1:
    def test_add_event_no_overflow(self):
        """Events within budget should not cause overflow."""
        wm = WorkingMemoryL1(max_tokens=500)
        overflow = wm.add_event(_event(tokens=100))
        assert overflow == []
        assert wm.event_count == 1
        assert wm.current_tokens == 100

    def test_overflow_evicts_oldest(self):
        """When budget exceeded, oldest events are evicted FIFO."""
        wm = WorkingMemoryL1(max_tokens=200)
        wm.add_event(_event("first", tokens=100))
        wm.add_event(_event("second", tokens=100))

        overflow = wm.add_event(_event("third", tokens=150))
        assert len(overflow) >= 1
        assert overflow[0].content == "first"

    def test_utilization_ratio(self):
        """Utilization reflects token usage vs budget."""
        wm = WorkingMemoryL1(max_tokens=1000)
        wm.add_event(_event(tokens=500))
        assert wm.utilization == pytest.approx(0.5)

    def test_clear_returns_buffer(self):
        """clear() returns all events and resets state."""
        wm = WorkingMemoryL1(max_tokens=1000)
        wm.add_event(_event("a", tokens=100))
        wm.add_event(_event("b", tokens=200))

        flushed = wm.clear()
        assert len(flushed) == 2
        assert wm.event_count == 0
        assert wm.current_tokens == 0

    def test_get_context_returns_message_dicts(self):
        """get_context() produces prompt-ready dicts."""
        wm = WorkingMemoryL1(max_tokens=1000)
        wm.add_event(_event("hello", role="user"))
        wm.add_event(_event("world", role="assistant"))

        ctx = wm.get_context()
        assert ctx == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]

    def test_invalid_max_tokens_raises(self):
        """max_tokens <= 0 must raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            WorkingMemoryL1(max_tokens=0)
        with pytest.raises(ValueError, match="positive"):
            WorkingMemoryL1(max_tokens=-1)

    def test_default_max_tokens(self):
        """Default budget should match the module constant."""
        wm = WorkingMemoryL1()
        assert wm.max_tokens == DEFAULT_MAX_TOKENS

    def test_len_matches_event_count(self):
        """__len__ should match event_count."""
        wm = WorkingMemoryL1(max_tokens=1000)
        assert len(wm) == 0
        wm.add_event(_event(tokens=100))
        assert len(wm) == 1

    def test_repr_is_informative(self):
        """__repr__ should contain useful state info."""
        wm = WorkingMemoryL1(max_tokens=1000)
        wm.add_event(_event(tokens=500))
        r = repr(wm)
        assert "events=1" in r
        assert "500/1000" in r

    def test_multi_eviction(self):
        """Multiple events should be evicted if a large event overflows."""
        wm = WorkingMemoryL1(max_tokens=300)
        wm.add_event(_event("a", tokens=100))
        wm.add_event(_event("b", tokens=100))
        wm.add_event(_event("c", tokens=100))

        # This 250-token event forces evicting a+b+c
        overflow = wm.add_event(_event("big", tokens=250))
        assert len(overflow) >= 2
        evicted_contents = [e.content for e in overflow]
        assert "a" in evicted_contents
        assert "b" in evicted_contents
