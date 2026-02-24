# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.1 — Sovereign Trace Layer (KETER-∞ Ola 4).

Zero-dependency structured tracing for CORTEX.
No OpenTelemetry, no Logfire — pure Python with contextvars propagation.

Architecture::

    @traced
    async def think(prompt):    ← auto-creates span, measures latency, captures errors
        with SpanContext("query_model"):  ← nested child span
            ...

    collector.spans  ← circular buffer of completed spans
    collector.export_metrics(registry)  ← push to MetricsRegistry histograms

Usage::

    from cortex.telemetry import traced, SpanContext, collector

    @traced
    async def my_operation():
        with SpanContext("sub_task"):
            ...

    # Access completed spans
    for span in collector.spans:
        print(span.name, span.duration_ms)
"""

from __future__ import annotations

import contextvars
import functools
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.telemetry.metrics import MetricsRegistry

__all__ = ["traced", "SpanContext", "Span", "TraceCollector", "collector"]

logger = logging.getLogger("cortex.telemetry")

# ─── Context propagation ────────────────────────────────────────────

_current_span: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
    "current_span", default=None
)


# ─── Data Models ─────────────────────────────────────────────────────


@dataclass(slots=True)
class Span:
    """A single trace span with timing and metadata."""

    name: str
    start_ns: int = 0
    end_ns: int = 0
    parent_name: str | None = None
    error: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        if self.end_ns <= 0 or self.start_ns <= 0:
            return 0.0
        return (self.end_ns - self.start_ns) / 1_000_000

    @property
    def ok(self) -> bool:
        return self.error is None

    def __repr__(self) -> str:
        status = "✓" if self.ok else f"✗ {self.error}"
        return f"Span({self.name}, {self.duration_ms:.1f}ms, {status})"


# ─── Trace Collector ─────────────────────────────────────────────────


class TraceCollector:
    """Circular-buffer collector for completed spans.

    Thread-safe via deque's atomic append. No locks needed.
    """

    def __init__(self, maxlen: int = 1000):
        self._buffer: deque[Span] = deque(maxlen=maxlen)

    def record(self, span: Span) -> None:
        """Record a completed span."""
        self._buffer.append(span)
        logger.debug("Span completed: %s", span)

    @property
    def spans(self) -> list[Span]:
        """Snapshot of all recorded spans."""
        return list(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()

    def export_metrics(self, registry: MetricsRegistry) -> int:
        """Push span durations to MetricsRegistry as histogram observations.

        Returns number of spans exported.
        """
        count = 0
        for span in self._buffer:
            registry.observe(
                "cortex_span_duration_ms",
                span.duration_ms,
                labels={"span": span.name, "status": "ok" if span.ok else "error"},
            )
            count += 1
        return count

    def __len__(self) -> int:
        return len(self._buffer)


# Global collector singleton
collector = TraceCollector()


# ─── SpanContext (context manager) ───────────────────────────────────


class SpanContext:
    """Context manager for creating nested spans.

    Usage::

        with SpanContext("operation_name", key="value") as span:
            # do work
            span.attributes["result"] = "success"
    """

    def __init__(self, name: str, **attributes: Any):
        self._name = name
        self._attributes = attributes
        self._span: Span | None = None
        self._token: contextvars.Token | None = None

    def __enter__(self) -> Span:
        parent = _current_span.get()
        self._span = Span(
            name=self._name,
            start_ns=time.monotonic_ns(),
            parent_name=parent.name if parent else None,
            attributes=dict(self._attributes),
        )
        self._token = _current_span.set(self._span)
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._span is None:
            return
        self._span.end_ns = time.monotonic_ns()
        if exc_val is not None:
            self._span.error = f"{type(exc_val).__name__}: {exc_val}"
        collector.record(self._span)
        if self._token is not None:
            _current_span.reset(self._token)
        return None  # Don't suppress exceptions


# ─── @traced Decorator ───────────────────────────────────────────────


def traced(fn=None, *, name: str | None = None):
    """Decorator that wraps a function in a tracing span.

    Works with both sync and async functions.

    Usage::

        @traced
        def sync_function(): ...

        @traced(name="custom_name")
        async def async_function(): ...
    """
    if fn is None:
        # Called with arguments: @traced(name="...")
        return functools.partial(traced, name=name)

    span_name = name or fn.__qualname__

    if _is_coroutine_function(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            with SpanContext(span_name):
                return await fn(*args, **kwargs)

        return async_wrapper
    else:

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            with SpanContext(span_name):
                return fn(*args, **kwargs)

        return sync_wrapper


def _is_coroutine_function(fn) -> bool:
    """Check if function is async, handling wrapped functions."""
    import inspect

    return inspect.iscoroutinefunction(fn)
