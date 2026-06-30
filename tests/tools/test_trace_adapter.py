"""Tests for trace_adapter and trace_builder.

Uses only deterministic fixtures — no live engine, no DB, no network.
Designed to run in CI without any external dependencies.
"""

from __future__ import annotations

import pytest

from babylon60.tools.trace_adapter import ExecutionTrace, TraceEvent
from babylon60.tools.trace_builder import TraceBuilder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def minimal_trace() -> ExecutionTrace:
    """Single-event trace: one write followed by a commit."""
    b = TraceBuilder(
        tenant_id="t1", model_version="test-0.1", op_kind="write", trace_id="trace-001"
    )
    b.record("write", fact_id="f1", ledger_height=100, payload_hash="aabbcc")
    b.record("commit", ledger_height=101)
    return b.build()


@pytest.fixture()
def mixed_trace() -> ExecutionTrace:
    """Multi-event trace with reads, writes and mutations."""
    b = TraceBuilder(
        tenant_id="t2", model_version="test-0.2", op_kind="mutation", trace_id="trace-002"
    )
    b.record("read", fact_id="f10", ledger_height=200)
    b.record("write", fact_id="f11", ledger_height=201, payload_hash="deadbeef")
    b.record("mutation", fact_id="f12", ledger_height=202)
    b.record("fact", fact_id="f13", ledger_height=203)
    b.record("commit", ledger_height=204)
    return b.build()


@pytest.fixture()
def empty_trace() -> ExecutionTrace:
    """Zero-event trace — edge case for all counters."""
    b = TraceBuilder(
        tenant_id=None, model_version="test-0.0", op_kind="query", trace_id="trace-000"
    )
    return b.build()


# ---------------------------------------------------------------------------
# TraceBuilder tests
# ---------------------------------------------------------------------------


class TestTraceBuilder:
    def test_trace_id_preserved(self, minimal_trace):
        assert minimal_trace.id == "trace-001"

    def test_length(self, minimal_trace):
        assert minimal_trace.length() == 2

    def test_empty_length(self, empty_trace):
        assert empty_trace.length() == 0

    def test_builder_len_matches_events(self):
        b = TraceBuilder(tenant_id="t", model_version="v", op_kind="write")
        assert len(b) == 0
        b.record("write")
        b.record("commit")
        assert len(b) == 2

    def test_wall_time_non_negative(self, minimal_trace):
        assert minimal_trace.wall_time() >= 0.0


# ---------------------------------------------------------------------------
# ExecutionTrace interface (Trajectory Protocol)
# ---------------------------------------------------------------------------


class TestExecutionTraceProtocol:
    def test_events_iterator(self, minimal_trace):
        evs = list(minimal_trace.events())
        assert len(evs) == 2
        assert all(isinstance(ev, TraceEvent) for ev in evs)

    def test_ledger_snapshot_returns_last_height(self, minimal_trace):
        assert minimal_trace.ledger_snapshot() == 101

    def test_ledger_snapshot_none_when_empty(self, empty_trace):
        assert empty_trace.ledger_snapshot() is None

    def test_counters(self, mixed_trace):
        assert mixed_trace.writes_count() == 1
        assert mixed_trace.reads_count() == 1
        assert mixed_trace.mutations_count() == 1

    def test_persisted_events(self, mixed_trace):
        # write + fact + commit = 3
        persisted = mixed_trace.persisted_events()
        assert len(persisted) == 3
        kinds = {ev.kind for ev in persisted}
        assert kinds == {"write", "fact", "commit"}

    def test_as_dict_keys(self, minimal_trace):
        d = minimal_trace.as_dict()
        required = {
            "id",
            "tenant_id",
            "model_version",
            "op_kind",
            "start_time",
            "end_time",
            "length",
            "ledger_snapshot",
            "wall_time",
            "writes",
            "reads",
            "mutations",
        }
        assert required.issubset(d.keys())

    def test_as_dict_values(self, minimal_trace):
        d = minimal_trace.as_dict()
        assert d["id"] == "trace-001"
        assert d["tenant_id"] == "t1"
        assert d["writes"] == 1
        assert d["reads"] == 0
        assert d["mutations"] == 0
        assert d["ledger_snapshot"] == 101


# ---------------------------------------------------------------------------
# TraceEvent field correctness
# ---------------------------------------------------------------------------


class TestTraceEventFlags:
    def test_write_flags(self):
        b = TraceBuilder(tenant_id=None, model_version="v", op_kind="write")
        b.record("write", ledger_height=10)
        trace = b.build()
        ev = next(trace.events())
        assert ev.is_write is True
        assert ev.is_read is False
        assert ev.is_mutation is False
        assert ev.is_persisted_event is True

    def test_read_flags(self):
        b = TraceBuilder(tenant_id=None, model_version="v", op_kind="query")
        b.record("read")
        trace = b.build()
        ev = next(trace.events())
        assert ev.is_read is True
        assert ev.is_write is False
        assert ev.is_persisted_event is False

    def test_mutation_not_persisted(self):
        b = TraceBuilder(tenant_id=None, model_version="v", op_kind="mutation")
        b.record("mutation")
        trace = b.build()
        ev = next(trace.events())
        assert ev.is_mutation is True
        assert ev.is_persisted_event is False
