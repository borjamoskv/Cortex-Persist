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
from typing import Any, Final, Optional

from cortex.memory.guardrails import SessionGuardrail
from cortex.memory.models import MemoryEvent

try:
    from cortex.extensions.security.tenant import get_tenant_id
except ImportError:
    def get_tenant_id() -> str:
        return "default"

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

    __slots__ = ("_buffers", "_tenant_tokens", "_max_tokens", "_guardrail", "_access_log")

    def __init__(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        guardrail: Optional[SessionGuardrail] = None,
    ) -> None:
        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")
        self._max_tokens = max_tokens
        # Per-tenant isolation: {tenant_id: deque[MemoryEvent]}
        self._buffers: dict[str, deque[MemoryEvent]] = {}
        # Per-tenant token usage: {tenant_id: current_tokens}
        self._tenant_tokens: dict[str, int] = {}
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
        score += max(0.0, 1.0 - (age_seconds / 3600))  # higher if < 1 hour old

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
        tenant_id = event.tenant_id

        # Session-level budget check (if guardrail attached)
        if self._guardrail is not None:
            if not self._guardrail.consume(event.token_count):
                msg = (
                    f"Session budget exhausted "
                    f"({self._guardrail.consumed}/{self._guardrail.max_tokens} tokens)"
                )
                raise RuntimeError(msg)

        # Record access BEFORE appending
        project_id: str = event.metadata.get("project_id", tenant_id)
        self._access_log.append((time.monotonic(), f"{tenant_id}:{project_id}"))

        # Initialize tenant buffer if needed
        if tenant_id not in self._buffers:
            self._buffers[tenant_id] = deque()
            self._tenant_tokens[tenant_id] = 0

        buffer = self._buffers[tenant_id]
        buffer.append(event)
        self._tenant_tokens[tenant_id] += event.token_count

        overflow: list[MemoryEvent] = []
        while self._tenant_tokens[tenant_id] > self._max_tokens and buffer:
            # Shift from pure FIFO to priority-weighted eviction
            lowest_priority = float("inf")
            evict_idx = 0
            for i, evt in enumerate(buffer):
                p = self._calculate_priority(evt)
                if p < lowest_priority:
                    lowest_priority = p
                    evict_idx = i

            evicted = buffer[evict_idx]
            buffer.remove(evicted)
            self._tenant_tokens[tenant_id] -= evicted.token_count
            overflow.append(evicted)

        if overflow:
            logger.debug(
                "L1 overflow [Tenant: %s]: evicted %d events (%d tokens freed)",
                tenant_id,
                len(overflow),
                sum(e.token_count for e in overflow),
            )

        return overflow

    def get_context(self, tenant_id: Optional[str] = None) -> list[dict[str, str]]:
        """Return current buffer for a tenant as prompt-ready message dicts."""
        tenant_id = tenant_id or get_tenant_id()
        if tenant_id not in self._buffers:
            return []

        now = time.monotonic()
        seen: set[str] = set()
        buffer = self._buffers[tenant_id]

        for e in buffer:
            pid = e.metadata.get("project_id", e.tenant_id)
            if pid not in seen:
                self._access_log.append((now, f"{tenant_id}:{pid}"))
                seen.add(pid)
        return [{"role": e.role, "content": e.content} for e in buffer]

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

    def clear(self, tenant_id: Optional[str] = None) -> list[MemoryEvent]:
        """Flush events. If tenant_id provided, clears ONLY that tenant."""
        flushed: list[MemoryEvent] = []
        if tenant_id:
            if tenant_id in self._buffers:
                flushed = list(self._buffers[tenant_id])
                self._buffers[tenant_id].clear()
                self._tenant_tokens[tenant_id] = 0
        else:
            # Clear all
            for buf in self._buffers.values():
                flushed.extend(buf)
            self._buffers.clear()
            self._tenant_tokens.clear()
        return flushed

    # ─── Snapshot & Export ────────────────────────────────────────

    def snapshot(self, tenant_id: Optional[str] = None) -> dict[str, Any]:
        """Export current working memory state as a portable dictionary."""
        resolved_tenant_id = tenant_id or get_tenant_id()
        if resolved_tenant_id not in self._buffers:
            return {"tenant_id": resolved_tenant_id, "tokens": 0, "events": []}

        return {
            "tenant_id": resolved_tenant_id,
            "tokens": self._tenant_tokens[resolved_tenant_id],
            "events": [
                e.model_dump() if hasattr(e, "model_dump") else e.dict()
                for e in self._buffers[resolved_tenant_id]
            ],
        }

    def restore(self, snapshot_data: dict[str, Any], tenant_id: Optional[str] = None) -> None:
        """Import working memory state from a snapshot dictionary."""
        resolved_tenant_id = tenant_id or snapshot_data.get("tenant_id") or get_tenant_id()
        if not resolved_tenant_id:
            raise ValueError("Cannot restore: resolved tenant_id is None or empty.")

        events_data = snapshot_data.get("events", [])
        events = []
        for e_data in events_data:
            if isinstance(e_data, dict):
                events.append(MemoryEvent(**e_data))
            else:
                events.append(e_data)

        self._buffers[resolved_tenant_id] = deque(events)
        self._tenant_tokens[resolved_tenant_id] = snapshot_data.get(
            "tokens", sum(e.token_count for e in events)
        )

    # ─── Introspection ────────────────────────────────────────────

    @property
    def current_tokens(self) -> int:
        """Current token usage for a tenant."""
        tenant_id = get_tenant_id()
        return self._tenant_tokens.get(tenant_id, 0)

    @property
    def max_tokens(self) -> int:
        """Maximum token budget per tenant."""
        return self._max_tokens

    def utilization(self, tenant_id: Optional[str] = None) -> float:
        """Token utilization ratio for a tenant."""
        tenant_id = tenant_id or get_tenant_id()
        if self._max_tokens == 0:
            return 0.0
        return self._tenant_tokens.get(tenant_id, 0) / self._max_tokens

    def event_count(self, tenant_id: Optional[str] = None) -> int:
        """Number of events in the buffer for a tenant."""
        tenant_id = tenant_id or get_tenant_id()
        return len(self._buffers.get(tenant_id, []))

    def __len__(self) -> int:
        """Total event count across all tenants."""
        return sum(len(b) for b in self._buffers.values())

    def __repr__(self) -> str:
        total_events = len(self)
        total_tokens = sum(self._tenant_tokens.values())
        return (
            f"WorkingMemoryL1(tenants={len(self._buffers)}, events={total_events}, "
            f"tokens={total_tokens}/{self._max_tokens})"
        )
