# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.3 — L1 Working Memory (Sliding Window).

Volatile, token-budgeted buffer that retains the N most recent
interaction events. When the budget overflows, oldest events are
evicted and returned for compression into L2 (Episodic Vector Store).

No I/O. No async. Pure in-memory speed.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Final

from cortex.memory.models import MemoryEvent

__all__ = ["WorkingMemoryL1"]

logger = logging.getLogger("cortex.memory.working")

DEFAULT_MAX_TOKENS: Final[int] = 8192


class WorkingMemoryL1:
    """Token-budgeted FIFO sliding window for short-term context.

    Args:
        max_tokens: Maximum token budget. Events are evicted FIFO
                    when this limit is exceeded.
    """

    __slots__ = ("_buffer", "_current_tokens", "_max_tokens")

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")
        self._max_tokens = max_tokens
        self._buffer: deque[MemoryEvent] = deque()
        self._current_tokens = 0

    # ─── Core Operations ──────────────────────────────────────────

    def add_event(self, event: MemoryEvent) -> list[MemoryEvent]:
        """Add an event, returning any overflow for L2 compression.

        Returns:
            List of evicted events (empty if no overflow).
        """
        self._buffer.append(event)
        self._current_tokens += event.token_count

        overflow: list[MemoryEvent] = []
        while self._current_tokens > self._max_tokens and self._buffer:
            evicted = self._buffer.popleft()
            self._current_tokens -= evicted.token_count
            overflow.append(evicted)

        if overflow:
            logger.debug(
                "L1 overflow: evicted %d events (%d tokens freed)",
                len(overflow),
                sum(e.token_count for e in overflow),
            )

        return overflow

    def get_context(self) -> list[dict[str, str]]:
        """Return current buffer as prompt-ready message dicts."""
        return [{"role": e.role, "content": e.content} for e in self._buffer]

    def clear(self) -> list[MemoryEvent]:
        """Flush all events. Returns the flushed buffer for archival."""
        flushed = list(self._buffer)
        self._buffer.clear()
        self._current_tokens = 0
        return flushed

    # ─── Introspection ────────────────────────────────────────────

    @property
    def current_tokens(self) -> int:
        """Current token usage."""
        return self._current_tokens

    @property
    def max_tokens(self) -> int:
        """Maximum token budget."""
        return self._max_tokens

    @property
    def utilization(self) -> float:
        """Token utilization ratio (0.0 - 1.0+)."""
        if self._max_tokens == 0:
            return 0.0
        return self._current_tokens / self._max_tokens

    @property
    def event_count(self) -> int:
        """Number of events in the buffer."""
        return len(self._buffer)

    def __len__(self) -> int:
        return len(self._buffer)

    def __repr__(self) -> str:
        return (
            f"WorkingMemoryL1(events={len(self._buffer)}, "
            f"tokens={self._current_tokens}/{self._max_tokens}, "
            f"util={self.utilization:.1%})"
        )
