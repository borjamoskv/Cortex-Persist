"""Tests for cortex.telemetry — Sovereign Trace Layer."""

from __future__ import annotations

import asyncio

import pytest

from cortex.telemetry import Span, SpanContext, TraceCollector, collector, traced


@pytest.fixture(autouse=True)
def _clear_collector():
    """Clear global collector before each test."""
    collector.clear()
    yield
    collector.clear()


class TestSpan:
    def test_duration(self):
        s = Span(name="test", start_ns=1_000_000, end_ns=2_000_000)
        assert s.duration_ms == pytest.approx(1.0)

    def test_ok(self):
        s = Span(name="ok")
        assert s.ok is True

    def test_error(self):
        s = Span(name="fail", error="boom")
        assert s.ok is False

    def test_repr_ok(self):
        s = Span(name="test", start_ns=0, end_ns=1_000_000)
        assert "✓" in repr(s)

    def test_repr_error(self):
        s = Span(name="test", error="oops")
        assert "✗" in repr(s)

    def test_zero_duration(self):
        s = Span(name="zero")
        assert s.duration_ms == pytest.approx(0.0)


class TestTraceCollector:
    def test_record_and_spans(self):
        tc = TraceCollector(maxlen=10)
        tc.record(Span(name="a", start_ns=1, end_ns=2))
        tc.record(Span(name="b", start_ns=3, end_ns=4))
        assert len(tc) == 2
        assert tc.spans[0].name == "a"

    def test_circular_buffer(self):
        tc = TraceCollector(maxlen=3)
        for i in range(5):
            tc.record(Span(name=f"span_{i}"))
        assert len(tc) == 3
        assert tc.spans[0].name == "span_2"  # Oldest evicted

    def test_clear(self):
        tc = TraceCollector()
        tc.record(Span(name="x"))
        tc.clear()
        assert len(tc) == 0

    def test_export_metrics(self):
        """Export pushes to a mock registry."""

        class MockRegistry:
            def __init__(self):
                self.observations = []

            def observe(self, name, value, labels=None):
                self.observations.append((name, value, labels))

        tc = TraceCollector()
        tc.record(Span(name="op", start_ns=1_000_000, end_ns=5_000_000))
        registry = MockRegistry()
        count = tc.export_metrics(registry)
        assert count == 1
        assert registry.observations[0][0] == "cortex_span_duration_ms"


class TestSpanContext:
    def test_basic_span(self):
        with SpanContext("test_op") as span:
            span.attributes["key"] = "value"

        assert len(collector) == 1
        s = collector.spans[0]
        assert s.name == "test_op"
        assert s.ok is True
        assert s.duration_ms > 0
        assert s.attributes["key"] == "value"

    def test_nested_spans(self):
        with SpanContext("parent"):
            with SpanContext("child"):
                x = 1  # noqa: F841 — work inside span

        assert len(collector) == 2
        child_span = collector.spans[0]  # Child completes first
        parent_span = collector.spans[1]
        assert child_span.parent_name == "parent"
        assert parent_span.parent_name is None

    def test_error_capture(self):
        with pytest.raises(ValueError, match="boom"):
            with SpanContext("failing"):
                raise ValueError("boom")

        s = collector.spans[0]
        assert s.ok is False
        assert "ValueError: boom" in s.error

    def test_attributes_on_init(self):
        with SpanContext("op", model="gpt-4o", mode="code"):
            x = 1  # noqa: F841 — work inside span

        s = collector.spans[0]
        assert s.attributes["model"] == "gpt-4o"
        assert s.attributes["mode"] == "code"


class TestTracedDecorator:
    def test_sync_function(self):
        @traced
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5
        assert len(collector) == 1
        assert collector.spans[0].name == "TestTracedDecorator.test_sync_function.<locals>.add"

    def test_async_function(self):
        @traced
        async def async_add(a, b):
            return a + b

        result = asyncio.run(async_add(2, 3))
        assert result == 5
        assert len(collector) == 1

    def test_custom_name(self):
        @traced(name="custom_op")
        def noop():
            return 0  # minimal operation

        noop()
        assert collector.spans[0].name == "custom_op"

    def test_error_in_traced(self):
        @traced
        def boom():
            raise RuntimeError("kaboom")

        with pytest.raises(RuntimeError, match="kaboom"):
            boom()

        assert len(collector) == 1
        assert collector.spans[0].ok is False
        assert "RuntimeError" in collector.spans[0].error

    def test_async_error(self):
        @traced
        async def async_boom():
            raise ValueError("async fail")

        with pytest.raises(ValueError, match="async fail"):
            asyncio.run(async_boom())

        assert len(collector) == 1
        assert collector.spans[0].ok is False
