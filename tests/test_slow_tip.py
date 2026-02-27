"""Tests for cortex.cli.slow_tip — SlowOpTipEmitter."""

from __future__ import annotations

import threading
import time

import pytest

from cortex.cli.slow_tip import SlowOpTipEmitter, tip_on_slow, with_slow_tips


class TestSlowOpTipEmitter:
    """Core emitter behavior."""

    def test_no_tip_on_fast_op(self):
        """Emitter must NOT fire if operation finishes before threshold."""
        emitted = []
        orig = SlowOpTipEmitter._emit_tip
        SlowOpTipEmitter._emit_tip = lambda self: emitted.append(1)
        try:
            e = SlowOpTipEmitter("test", threshold=10.0)
            e.start()
            time.sleep(0.05)  # Fast op — well under threshold
            e.stop()
        finally:
            SlowOpTipEmitter._emit_tip = orig

        assert emitted == [], "No tip should fire for fast operations"

    def test_tip_fires_after_threshold(self):
        """Emitter MUST fire after threshold seconds."""
        emitted = []
        event = threading.Event()

        orig = SlowOpTipEmitter._emit_tip

        def _fake_emit(self):
            emitted.append(1)
            event.set()

        SlowOpTipEmitter._emit_tip = _fake_emit
        try:
            e = SlowOpTipEmitter("test", threshold=0.1, interval=60.0)
            e.start()
            fired = event.wait(timeout=1.0)
            e.stop()
        finally:
            SlowOpTipEmitter._emit_tip = orig

        assert fired, "Tip should fire after threshold"
        assert len(emitted) >= 1

    def test_multiple_tips_at_interval(self):
        """Emitter fires repeatedly at interval after threshold."""
        emitted = []
        orig = SlowOpTipEmitter._emit_tip
        SlowOpTipEmitter._emit_tip = lambda self: emitted.append(time.monotonic())
        try:
            e = SlowOpTipEmitter("test", threshold=0.05, interval=0.1)
            e.start()
            time.sleep(0.45)  # Should get ~3 tips (threshold + 2 intervals)
            e.stop()
        finally:
            SlowOpTipEmitter._emit_tip = orig

        assert len(emitted) >= 2, f"Expected >=2 tips, got {len(emitted)}"

    def test_context_manager_stops_cleanly(self):
        """Context manager must stop the thread on exit."""
        with with_slow_tips("test", threshold=60.0) as emitter:
            assert emitter._thread.is_alive()
        # After exit the thread should be stopped
        time.sleep(0.05)
        assert not emitter._thread.is_alive()

    def test_daemon_thread(self):
        """Emitter thread must be daemonized (won't prevent process exit)."""
        e = SlowOpTipEmitter("test", threshold=60.0)
        e.start()
        assert e._thread.daemon
        e.stop()

    def test_stop_idempotent(self):
        """Calling stop() multiple times must not raise."""
        e = SlowOpTipEmitter("test", threshold=60.0)
        e.start()
        e.stop()
        e.stop()  # Must not raise

    def test_never_crashes_on_import_error(self, monkeypatch):
        """_emit_tip must never raise — tips are non-critical."""
        import sys
        # Simulate tips import failure
        monkeypatch.setitem(sys.modules, "cortex.cli.tips", None)

        e = SlowOpTipEmitter("test", threshold=0.0, interval=60.0)
        # Should not raise
        e._emit_tip()


class TestTipOnSlowDecorator:
    """@tip_on_slow decorator."""

    def test_decorator_preserves_return_value(self):
        """Decorated function must return the same value."""
        @tip_on_slow(threshold=60.0)
        def _fast():
            return 42

        assert _fast() == 42

    def test_decorator_preserves_function_name(self):
        """@functools.wraps must be applied."""
        @tip_on_slow(threshold=60.0)
        def my_func():
            pass

        assert my_func.__name__ == "my_func"

    def test_decorator_passes_args_kwargs(self):
        """Args and kwargs must reach the wrapped function."""
        @tip_on_slow(threshold=60.0)
        def add(a, b, c=0):
            return a + b + c

        assert add(1, 2, c=3) == 6

    def test_decorator_propagates_exceptions(self):
        """Exceptions from the wrapped function must propagate."""
        @tip_on_slow(threshold=60.0)
        def boom():
            raise ValueError("intentional")

        with pytest.raises(ValueError, match="intentional"):
            boom()
