# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
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
import time
from collections import deque
from typing import Final

from cortex.memory.guardrails import SessionGuardrail
from cortex.memory.models import MemoryEvent

__all__ = ["WorkingMemoryL1"]

logger = logging.getLogger("cortex.memory.working")

DEFAULT_MAX_TOKENS: Final[int] = 8192
# Rolling access history: max 2 048 entries to keep memory footprint bounded (≈48 KB worst-case)
_ACCESS_LOG_MAXLEN: Final[int] = 2048


class WorkingMemoryL1:
    """Token-budgeted FIFO sliding window for short-term context.

    Args:
        max_tokens: Maximum token budget. Events are evicted FIFO
                    when this limit is exceeded.
    """

    __slots__ = ("_buffer", "_current_tokens", "_max_tokens", "_guardrail", "_access_log")

    def __init__(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        guardrail: SessionGuardrail | None = None,
    ) -> None:
        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")
        self._max_tokens = max_tokens
        self._buffer: deque[MemoryEvent] = deque()
        self._current_tokens = 0
        self._guardrail = guardrail
        # Access log: deque of (monotonic_ts, project_id) tuples.
        # Written by add_event + get_context; read by ForgettingOracle.
        # maxlen caps memory irrespective of session length (Ω₂ — Entropic Asymmetry).
        self._access_log: deque[tuple[float, str]] = deque(maxlen=_ACCESS_LOG_MAXLEN)

    # ─── Core Operations ──────────────────────────────────────────

    def _calculate_priority(self, event: MemoryEvent) -> float:
        """Lightweight heuristic to determine event retention priority."""
        score = 1.0
        # 1. Recency (base priority)
        age_seconds = time.time() - event.timestamp.timestamp()
        score += max(0, 1.0 - (age_seconds / 3600))  # higher if < 1 hour old

        # 2. Emotion/Valence
        meta_valence = event.metadata.get("valence", 0.0)
        score += abs(float(meta_valence)) * 0.5

        # 3. Role importance
        if event.role == "user":
            score += 0.5
        elif event.role == "system":
            score += 1.0

        return score

    def add_event(self, event: MemoryEvent) -> list[MemoryEvent]:
        """Add an event, returning any overflow for L2 compression.

        Returns:
            List of evicted events (empty if no overflow).

        Raises:
            RuntimeError: If the session guardrail rejects the event.
        """
        # Session-level budget check (if guardrail attached)
        if self._guardrail is not None:
            if not self._guardrail.consume(event.token_count):
                msg = (
                    f"Session budget exhausted "
                    f"({self._guardrail.consumed}/{self._guardrail.max_tokens} tokens)"
                )
                raise RuntimeError(msg)

        # Record access BEFORE appending — so the Oracle can distinguish
        # write-access from read-access if needed in future iterations.
        project_id: str = event.metadata.get("project_id", event.tenant_id)
        self._access_log.append((time.monotonic(), project_id))

        self._buffer.append(event)
        self._current_tokens += event.token_count

        overflow: list[MemoryEvent] = []
        while self._current_tokens > self._max_tokens and self._buffer:
            # Shift from pure FIFO to priority-weighted eviction (Central Executive)
            lowest_priority = float('inf')
            evict_idx = 0
            for i, evt in enumerate(self._buffer):
                p = self._calculate_priority(evt)
                if p < lowest_priority:
                    lowest_priority = p
                    evict_idx = i

            evicted = self._buffer[evict_idx]
            del self._buffer[evict_idx]
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
        """Return current buffer as prompt-ready message dicts.

        Also ticks the access log for every active project in the buffer
        so read-access patterns are captured (not only write-access).
        """
        now = time.monotonic()
        seen: set[str] = set()
        for e in self._buffer:
            pid = e.metadata.get("project_id", e.tenant_id)
            if pid not in seen:
                self._access_log.append((now, pid))
                seen.add(pid)
        return [{"role": e.role, "content": e.content} for e in self._buffer]

    def get_access_frequency(self, project_id: str, window_seconds: float = 3600.0) -> float:
        """Return normalised access frequency for a project_id in the last window_seconds.

        Reads directly from the in-memory rolling log — zero I/O, O(n) with
        n ≤ _ACCESS_LOG_MAXLEN (2 048).  A full log queried in the worst case
        completes in < 50 µs on modern hardware.

        Args:
            project_id: The project whose access frequency to measure.
            window_seconds: Rolling observation window (default 1 hour).

        Returns:
            Float in [0.0, 1.0] where 1.0 means ≥ 100 accesses in window.
        """
        if not self._access_log:
            return 0.0
        cutoff = time.monotonic() - window_seconds
        count = sum(1 for ts, pid in self._access_log if ts > cutoff and pid == project_id)
        # Normalise: 100+ accesses in window → 1.0  (Ω₁: right scale matters)
        return min(1.0, count / 100.0)

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
