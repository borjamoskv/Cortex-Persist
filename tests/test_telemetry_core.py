"""
Tests for cortex.telemetry.core
────────────────────────────────
Coverage targets:
  - Span.duration_ms, Span.ok
  - TraceCollector: record, spans, clear, len, export_metrics
  - SpanContext: timing, parent propagation, error capture, no suppression
  - traced: sync + async, custom name, error propagation
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

import pytest

# Reset global collector before each test to avoid cross-test bleed.
from cortex.telemetry.core import (
    Span,
    SpanContext,
    TraceCollector,
    collector,
    traced,
)

# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_collector():
    """Ensure global collector is clean before and after every test."""
    collector.clear()
    yield
    collector.clear()


# ─── Span ─────────────────────────────────────────────────────────────


class TestSpan:
    def test_duration_ms_happy(self):
        start = time.monotonic_ns()
        end = start + 5_000_000  # 5ms in ns
        s = Span(name="op", start_ns=start, end_ns=end)
        assert abs(s.duration_ms - 5.0) < 0.01

    def test_duration_ms_zero_when_unfinished(self):
        s = Span(name="op", start_ns=time.monotonic_ns(), end_ns=0)
        assert s.duration_ms == 0.0

    def test_ok_true_when_no_error(self):
        s = Span(name="op")
        assert s.ok is True

    def test_ok_false_when_error_set(self):
        s = Span(name="op", error="RuntimeError: boom")
        assert s.ok is False

    def test_repr_contains_name(self):
        s = Span(name="my_op")
        assert "my_op" in repr(s)


# ─── TraceCollector ───────────────────────────────────────────────────


class TestTraceCollector:
    def test_record_and_len(self):
        tc = TraceCollector(maxlen=10)
        s = Span(name="a", start_ns=1, end_ns=2)
        tc.record(s)
        assert len(tc) == 1

    def test_circular_buffer_maxlen(self):
        tc = TraceCollector(maxlen=3)
        for i in range(5):
            tc.record(Span(name=f"s{i}", start_ns=i, end_ns=i + 1))
        assert len(tc) == 3
        # Oldest should be evicted: s0, s1 dropped
        assert tc.spans[0].name == "s2"

    def test_clear(self):
        tc = TraceCollector()
        tc.record(Span(name="x"))
        tc.clear()
        assert len(tc) == 0

    def test_spans_snapshot(self):
        tc = TraceCollector()
        tc.record(Span(name="a"))
        snapshot = tc.spans
        tc.clear()
        # Snapshot is independent
        assert len(snapshot) == 1

    def test_export_metrics_calls_observe(self):
        tc = TraceCollector()
        start = time.monotonic_ns()
        end = start + 2_000_000  # 2ms
        tc.record(Span(name="tracked", start_ns=start, end_ns=end))

        registry = MagicMock()
        count = tc.export_metrics(registry)
        assert count == 1
        registry.observe.assert_called_once()
        call_kwargs = registry.observe.call_args
        assert "cortex_span_duration_ms" in call_kwargs[0]

    def test_export_metrics_error_span_label(self):
        tc = TraceCollector()
        s = Span(name="fail", start_ns=1, end_ns=2, error="ValueError: bad")
        tc.record(s)
        registry = MagicMock()
        tc.export_metrics(registry)
        _, kwargs = registry.observe.call_args
        # labels dict should contain status=error
        labels = registry.observe.call_args[1].get("labels") or registry.observe.call_args[0][2]
        assert labels.get("status") == "error"


# ─── SpanContext ──────────────────────────────────────────────────────


class TestSpanContext:
    def test_span_recorded_on_exit(self):
        with SpanContext("unit_op"):
            pass
        assert len(collector) == 1
        assert collector.spans[0].name == "unit_op"

    def test_duration_is_positive(self):
        with SpanContext("timed"):
            time.sleep(0.01)
        span = collector.spans[0]
        assert span.duration_ms >= 10.0

    def test_error_captured_on_exception(self):
        with pytest.raises(ValueError):
            with SpanContext("failing"):
                raise ValueError("expected")
        span = collector.spans[0]
        assert span.ok is False
        assert "ValueError" in span.error

    def test_exception_not_suppressed(self):
        with pytest.raises(RuntimeError):
            with SpanContext("propagate"):
                raise RuntimeError("should propagate")

    def test_attributes_stored(self):
        with SpanContext("tagged", key="value") as span:
            span.attributes["extra"] = 42
        recorded = collector.spans[0]
        assert recorded.attributes["key"] == "value"
        assert recorded.attributes["extra"] == 42

    def test_parent_propagation(self):
        with SpanContext("parent"):
            with SpanContext("child"):
                pass
        spans = collector.spans
        # child recorded first due to inner exit
        child = next(s for s in spans if s.name == "child")
        assert child.parent_name == "parent"

    def test_returns_span_from_enter(self):
        with SpanContext("ret") as s:
            assert isinstance(s, Span)
            assert s.name == "ret"


# ─── @traced decorator ────────────────────────────────────────────────


class TestTraced:
    def test_sync_function_traced(self):
        @traced
        def add(a, b):
            return a + b

        result = add(1, 2)
        assert result == 3
        assert len(collector) == 1
        assert "add" in collector.spans[0].name

    def test_sync_error_captured(self):
        @traced
        def explode():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            explode()
        span = collector.spans[0]
        assert not span.ok
        assert "ValueError" in span.error

    def test_async_function_traced(self):
        @traced
        async def fetch():
            await asyncio.sleep(0)
            return "data"

        result = asyncio.get_event_loop().run_until_complete(fetch())
        assert result == "data"
        assert len(collector) == 1

    def test_async_error_captured(self):
        @traced
        async def async_fail():
            raise RuntimeError("async boom")

        with pytest.raises(RuntimeError):
            asyncio.get_event_loop().run_until_complete(async_fail())
        assert not collector.spans[0].ok

    def test_custom_name(self):
        @traced(name="custom_op")
        def fn():
            pass

        fn()
        assert collector.spans[0].name == "custom_op"

    def test_return_value_preserved(self):
        @traced
        def identity(x):
            return x * 2

        assert identity(21) == 42

    def test_global_collector_receives_span(self):
        @traced
        def work():
            pass

        work()
        assert len(collector.spans) == 1
