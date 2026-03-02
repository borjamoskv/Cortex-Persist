"""Tests for CORTEX Signal Bus — L1 Consciousness Layer."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

import pytest

from cortex.signals.bus import SignalBus
from cortex.signals.models import Signal


@pytest.fixture
def bus(tmp_path):
    """Create a SignalBus with a temp database."""
    db_path = tmp_path / "test_signals.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    sb = SignalBus(conn)
    sb.ensure_table()
    yield sb
    conn.close()


class TestEmitAndPoll:
    """Emit → poll → consumed → second poll empty."""

    def test_emit_returns_id(self, bus):
        sid = bus.emit("plan:done", {"files": ["a.py"]}, source="arkitetv-1")
        assert isinstance(sid, int)
        assert sid > 0

    def test_poll_returns_emitted_signal(self, bus):
        bus.emit("plan:done", {"project": "cortex"}, source="test")
        signals = bus.poll(event_type="plan:done", consumer="legion-1")
        assert len(signals) == 1
        assert signals[0].event_type == "plan:done"
        assert signals[0].payload == {"project": "cortex"}
        assert signals[0].source == "test"

    def test_poll_consumes_signal(self, bus):
        bus.emit("plan:done", {}, source="test")
        first = bus.poll(event_type="plan:done", consumer="legion-1")
        assert len(first) == 1
        # Second poll by same consumer returns empty
        second = bus.poll(event_type="plan:done", consumer="legion-1")
        assert len(second) == 0

    def test_different_consumer_can_poll_same_signal(self, bus):
        bus.emit("build:success", {}, source="test")
        a = bus.poll(consumer="consumer-a")
        b = bus.poll(consumer="consumer-b")
        assert len(a) == 1
        assert len(b) == 1
        assert a[0].id == b[0].id


class TestPeek:
    """Peek does not consume."""

    def test_peek_does_not_consume(self, bus):
        bus.emit("error:critical", {"trace": "x"}, source="test")
        peeked = bus.peek(event_type="error:critical")
        assert len(peeked) == 1
        # Poll should still return the signal
        polled = bus.poll(event_type="error:critical", consumer="test")
        assert len(polled) == 1
        assert polled[0].id == peeked[0].id

    def test_peek_filters_by_consumer(self, bus):
        bus.emit("a", {}, source="test")
        bus.poll(consumer="c1")
        # Peek for c1 should return nothing (already consumed)
        peeked = bus.peek(consumer="c1")
        assert len(peeked) == 0
        # Peek for c2 should still see it
        peeked = bus.peek(consumer="c2")
        assert len(peeked) == 1


class TestFilter:
    """Filtering by type, source, project."""

    def test_filter_by_type(self, bus):
        bus.emit("plan:done", {}, source="test")
        bus.emit("error:critical", {}, source="test")
        bus.emit("plan:done", {}, source="test")

        signals = bus.poll(event_type="plan:done", consumer="test")
        assert len(signals) == 2
        assert all(s.event_type == "plan:done" for s in signals)

    def test_filter_by_source(self, bus):
        bus.emit("a", {}, source="arkitetv-1")
        bus.emit("a", {}, source="legion-1")

        signals = bus.poll(source="legion-1", consumer="test")
        assert len(signals) == 1
        assert signals[0].source == "legion-1"

    def test_filter_by_project(self, bus):
        bus.emit("a", {}, source="test", project="cortex")
        bus.emit("a", {}, source="test", project="naroa")

        signals = bus.poll(project="cortex", consumer="test")
        assert len(signals) == 1
        assert signals[0].project == "cortex"


class TestHistory:
    """History returns all including consumed, newest first."""

    def test_history_includes_consumed(self, bus):
        bus.emit("a", {}, source="test")
        bus.emit("b", {}, source="test")
        bus.poll(consumer="test")  # Consume all

        history = bus.history()
        assert len(history) == 2
        # Newest first
        assert history[0].event_type == "b"
        assert history[1].event_type == "a"

    def test_history_filter_by_type(self, bus):
        bus.emit("a", {}, source="test")
        bus.emit("b", {}, source="test")

        history = bus.history(event_type="a")
        assert len(history) == 1


class TestStats:
    """Stats aggregation."""

    def test_stats_empty(self, bus):
        s = bus.stats()
        assert s["total"] == 0
        assert s["unconsumed"] == 0

    def test_stats_counts(self, bus):
        bus.emit("plan:done", {}, source="arkitetv-1")
        bus.emit("plan:done", {}, source="arkitetv-1")
        bus.emit("error:critical", {}, source="trampolin")

        s = bus.stats()
        assert s["total"] == 3
        assert s["unconsumed"] == 3
        assert s["by_type"]["plan:done"] == 2
        assert s["by_type"]["error:critical"] == 1
        assert s["by_source"]["arkitetv-1"] == 2

    def test_stats_after_consume(self, bus):
        bus.emit("a", {}, source="test")
        bus.poll(consumer="test")

        s = bus.stats()
        assert s["total"] == 1
        assert s["unconsumed"] == 0


class TestGarbageCollection:
    """GC prunes old consumed signals only."""

    def test_gc_prunes_consumed(self, bus):
        # Emit and consume
        bus.emit("old", {}, source="test")
        bus.poll(consumer="test")

        # Backdate the signal to 60 days ago
        cutoff = (datetime.now() - timedelta(days=60)).isoformat()
        bus._conn.execute(
            "UPDATE signals SET created_at = ?", (cutoff,)
        )
        bus._conn.commit()

        pruned = bus.gc(max_age_days=30)
        assert pruned == 1

    def test_gc_preserves_unconsumed(self, bus):
        bus.emit("fresh", {}, source="test")

        # Backdate but don't consume
        cutoff = (datetime.now() - timedelta(days=60)).isoformat()
        bus._conn.execute(
            "UPDATE signals SET created_at = ?", (cutoff,)
        )
        bus._conn.commit()

        pruned = bus.gc(max_age_days=30)
        assert pruned == 0  # Not consumed, so not pruned


class TestSignalModel:
    """Signal model properties."""

    def test_is_consumed(self, bus):
        bus.emit("a", {}, source="test")
        peeked = bus.peek()
        assert not peeked[0].is_consumed

        bus.poll(consumer="test")
        history = bus.history()
        assert history[0].is_consumed

    def test_was_consumed_by(self, bus):
        bus.emit("a", {}, source="test")
        bus.poll(consumer="legion-1")

        history = bus.history()
        assert history[0].was_consumed_by("legion-1")
        assert not history[0].was_consumed_by("arkitetv-1")


class TestCLI:
    """CLI integration via CliRunner."""

    def test_cli_emit_and_history(self, tmp_path):
        from click.testing import CliRunner
        from cortex.cli.signal_cmds import signal_cmds

        db = str(tmp_path / "cli_test.db")
        runner = CliRunner()

        # Emit
        result = runner.invoke(
            signal_cmds,
            ["emit", "test:event", '{"key": "val"}', "--db", db],
        )
        assert result.exit_code == 0
        assert "Signal emitted" in result.output

        # History
        result = runner.invoke(
            signal_cmds,
            ["history", "--db", db],
        )
        assert result.exit_code == 0
        assert "test:event" in result.output

        # Stats
        result = runner.invoke(
            signal_cmds,
            ["stats", "--db", db],
        )
        assert result.exit_code == 0
        assert "Total signals" in result.output


class TestFactHook:
    """fact_hook.emit_fact_stored integration — L1 neural seed."""

    def test_emit_fact_stored_creates_signal(self, tmp_path):
        """emit_fact_stored persists a fact:stored signal."""
        from cortex.signals.fact_hook import emit_fact_stored
        from cortex.signals.bus import SignalBus

        db = str(tmp_path / "hook_test.db")
        emit_fact_stored(
            db_path=db,
            fact_id=42,
            project="cortex",
            fact_type="decision",
            source="agent:gemini",
            tenant_id="default",
            total_facts=100,
        )

        conn = __import__("sqlite3").connect(db)
        bus = SignalBus(conn)
        signals = bus.history(event_type="fact:stored")
        assert len(signals) == 1
        sig = signals[0]
        assert sig.payload["fact_id"] == 42
        assert sig.payload["project"] == "cortex"
        assert sig.payload["fact_type"] == "decision"
        assert sig.payload["source"] == "agent:gemini"
        assert sig.payload["total_facts"] == 100
        assert sig.source == "agent:gemini"
        assert sig.project == "cortex"
        conn.close()

    def test_emit_fact_stored_never_raises(self, tmp_path):
        """The hook must never propagate exceptions — fire-and-forget."""
        from cortex.signals.fact_hook import emit_fact_stored

        # Invalid path — should silently succeed
        emit_fact_stored(
            db_path="/nonexistent/path/to/cortex.db",
            fact_id=1,
            project="cortex",
            fact_type="decision",
            source="cli",
        )
        # No exception = pass

    def test_compact_needed_emitted_at_threshold(self, tmp_path):
        """compact:needed is emitted when unconsumed fact:stored >= threshold."""
        import os
        import sqlite3
        from cortex.signals.fact_hook import emit_fact_stored
        from cortex.signals.bus import SignalBus

        db = str(tmp_path / "threshold_test.db")
        threshold = 3
        os.environ["CORTEX_COMPACT_THRESHOLD"] = str(threshold)
        try:
            # Emit exactly threshold times
            for i in range(threshold):
                emit_fact_stored(
                    db_path=db,
                    fact_id=i + 1,
                    project="cortex",
                    fact_type="decision",
                    source="cli",
                )

            conn = sqlite3.connect(db)
            bus = SignalBus(conn)
            compact_signals = bus.history(event_type="compact:needed")
            assert len(compact_signals) >= 1
            assert compact_signals[0].project == "cortex"
            assert compact_signals[0].payload["threshold"] == threshold
            conn.close()
        finally:
            os.environ.pop("CORTEX_COMPACT_THRESHOLD", None)

    def test_compact_needed_not_emitted_below_threshold(self, tmp_path):
        """compact:needed is NOT emitted when below the threshold."""
        import os
        import sqlite3
        from cortex.signals.fact_hook import emit_fact_stored
        from cortex.signals.bus import SignalBus

        db = str(tmp_path / "below_threshold.db")
        threshold = 10
        os.environ["CORTEX_COMPACT_THRESHOLD"] = str(threshold)
        try:
            # Emit just below threshold
            for i in range(threshold - 1):
                emit_fact_stored(
                    db_path=db,
                    fact_id=i + 1,
                    project="naroa",
                    fact_type="knowledge",
                    source="cli",
                )

            conn = sqlite3.connect(db)
            bus = SignalBus(conn)
            compact_signals = bus.history(event_type="compact:needed")
            assert len(compact_signals) == 0
            conn.close()
        finally:
            os.environ.pop("CORTEX_COMPACT_THRESHOLD", None)
