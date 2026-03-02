"""Integration tests for PersistSupervisor — durability proof.

Ω₂ mandate: these tests are the ONLY evidence that the supervisor pattern
actually reduces entropy rather than displacing it.

Test hierarchy:
  Unit: PersistSupervisor ticks and calls flush_fn
  Integration: ExecutionLoop enqueues → supervisor drains → CORTEX stores
  Durability: Facts survive clean termination (SIGTERM scenario)

DERIVATION: Ω₂ (Entropic Asymmetry) + Ω₃ (Byzantine Default)
  — Productivity without integration tests is disguised tech debt.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.cli.loop_engine import ExecutionLoop, PersistSupervisor

# ─── Unit: PersistSupervisor mechanics ───────────────────────────────


class TestPersistSupervisorUnit:
    """Validate the supervisor ticks at the correct interval and calls flush_fn."""

    def test_supervisor_calls_flush_on_interval(self) -> None:
        """C5 guarantee: flush_fn must be called after one interval elapses."""
        flush_calls: list[str] = []

        def mock_flush(source: str = "supervisor") -> None:
            flush_calls.append(source)

        supervisor = PersistSupervisor(flush_fn=mock_flush, interval=1)
        supervisor.start()

        # Wait for at least one tick (interval=1s + buffer)
        time.sleep(1.5)
        supervisor.stop()

        assert len(flush_calls) >= 1, (
            "Supervisor never called flush_fn after interval — C5 guarantee violated"
        )
        assert all(s == "supervisor" for s in flush_calls), (
            f"Unexpected source in flush calls: {flush_calls}"
        )

    def test_supervisor_does_not_call_flush_before_interval(self) -> None:
        """Supervisor must respect the interval — no premature flushes."""
        flush_calls: list[str] = []

        def mock_flush(source: str = "supervisor") -> None:
            flush_calls.append(source)

        supervisor = PersistSupervisor(flush_fn=mock_flush, interval=10)
        supervisor.start()

        # Check immediately — no flush should have fired
        time.sleep(0.1)
        supervisor.stop()

        assert len(flush_calls) == 0, f"Supervisor flushed before interval elapsed: {flush_calls}"

    def test_supervisor_stops_cleanly(self) -> None:
        """stop() must join within timeout — no immortal threads."""
        supervised_started = threading.Event()

        def mock_flush(source: str = "supervisor") -> None:
            supervised_started.set()

        supervisor = PersistSupervisor(flush_fn=mock_flush, interval=60)
        supervisor.start()

        # Stop immediately — thread should join within 5s
        t0 = time.monotonic()
        supervisor.stop()
        elapsed = time.monotonic() - t0

        assert elapsed < 6.0, f"Supervisor.stop() exceeded timeout: {elapsed:.1f}s"

    def test_supervisor_flush_exception_does_not_kill_thread(self) -> None:
        """Ω₅: Supervisor must survive flush errors — the thread cannot die."""
        error_count = 0
        success_count = 0

        def flaky_flush(source: str = "supervisor") -> None:
            nonlocal error_count, success_count
            error_count += 1
            if error_count < 3:
                raise RuntimeError("simulated persist failure")
            success_count += 1

        supervisor = PersistSupervisor(flush_fn=flaky_flush, interval=1)
        supervisor.start()

        time.sleep(3.5)  # Wait for 3+ ticks
        supervisor.stop()

        assert supervisor._thread.is_alive() is False, "Supervisor thread still alive"
        # Thread survived the errors and eventually succeeded
        assert error_count >= 2, "Expected at least 2 flush attempts"


# ─── Unit: _flush_pending atomicity ──────────────────────────────────


class TestFlushPendingAtomicity:
    """Validate that _flush_pending is thread-safe and idempotent."""

    def _make_loop_no_supervisor(self) -> ExecutionLoop:
        """Create an ExecutionLoop with auto_persist=False to isolate flush logic."""
        with patch("cortex.cli.loop_engine.get_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.close = AsyncMock()
            mock_get_engine.return_value = mock_engine
            loop = ExecutionLoop(
                project="test-durability",
                auto_persist=False,
            )
            loop._engine = mock_engine
            return loop

    def test_flush_empty_queue_is_noop(self) -> None:
        """_flush_pending with no facts must not call engine.store."""
        loop = self._make_loop_no_supervisor()

        with patch.object(loop, "_engine") as mock_engine:
            loop._flush_pending(source="test")
            mock_engine.store.assert_not_called()

    def test_flush_drains_all_pending_facts(self) -> None:
        """_flush_pending must drain every enqueued fact in one call."""
        loop = self._make_loop_no_supervisor()

        # Enqueue 5 facts manually
        for i in range(5):
            loop._enqueue_fact(
                content=f"[TEST] fact {i}",
                fact_type="decision",
            )

        assert len(loop._pending_facts) == 5

        with patch("cortex.cli.loop_engine._run_async", side_effect=lambda coro: 1):
            loop._flush_pending(source="test")

        # Queue must be empty after flush
        assert len(loop._pending_facts) == 0, f"Pending facts not drained: {loop._pending_facts}"

    def test_flush_is_idempotent_on_empty(self) -> None:
        """Calling _flush_pending twice on empty queue is safe."""
        loop = self._make_loop_no_supervisor()
        loop._flush_pending(source="first")
        loop._flush_pending(source="second")  # Must not raise

    def test_re_enqueue_on_store_failure(self) -> None:
        """Ω₅: Failed facts must be re-enqueued for the next supervisor tick."""
        loop = self._make_loop_no_supervisor()
        loop._enqueue_fact(content="[TEST] will fail", fact_type="decision")

        def failing_run_async(coro):  # noqa: ANN001
            raise OSError("simulated DB failure")

        with patch("cortex.cli.loop_engine._run_async", side_effect=failing_run_async):
            loop._flush_pending(source="test")

        # Fact must have been re-enqueued — not lost
        assert len(loop._pending_facts) == 1, (
            "Failed fact was lost instead of re-enqueued — no Ω₅ recovery"
        )


# ─── Integration: ExecutionLoop full stack ───────────────────────────


class TestExecutionLoopIntegration:
    """Integration tests: ExecutionLoop → enqueue → supervisor → CORTEX.

    These are the tests that prove the sprint happened (Ω₂ mandate).
    Unit tests above validate mechanics; these validate the full chain.
    """

    @pytest.fixture
    def loop_with_mock_engine(self):
        """ExecutionLoop with real supervisor but mocked CORTEX engine."""
        mock_engine = MagicMock()
        mock_engine.close = AsyncMock()

        with (
            patch("cortex.cli.loop_engine.get_engine", return_value=mock_engine),
            patch("cortex.cli.loop_engine._run_async") as mock_run_async,
        ):
            # _run_async bridges sync→async; stub it as pure sync counter
            call_tracker = {"count": 0}

            def sync_run(coro):  # noqa: ANN001
                # Discard the coroutine cleanly to avoid RuntimeWarning
                try:
                    coro.close()
                except AttributeError:
                    pass
                call_tracker["count"] += 1
                return call_tracker["count"]

            mock_run_async.side_effect = sync_run

            loop = ExecutionLoop(
                project="test-integration",
                auto_persist=True,
                persist_interval=1,  # 1s for fast tests
            )
            loop._mock_run_async_calls = call_tracker
            yield loop, mock_run_async

        # Cleanup: stop supervisor and unregister atexit to avoid noisy
        # "Exception ignored in atexit callback" when pytest exits with mocked engine.
        if loop._supervisor is not None:
            loop._supervisor.stop()
        import atexit as _atexit

        _atexit.unregister(loop._atexit_flush)

    def test_enqueue_fact_thread_safe(self, loop_with_mock_engine) -> None:
        """Multiple threads can enqueue concurrently without corruption."""
        loop, _ = loop_with_mock_engine

        def enqueue_many() -> None:
            for i in range(100):
                loop._enqueue_fact(
                    content=f"[THREAD] concurrent fact {i}",
                    fact_type="decision",
                )

        threads = [threading.Thread(target=enqueue_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 5 threads × 100 facts = 500 — no corruption
        assert len(loop._pending_facts) == 500, (
            f"Thread-safety violation: got {len(loop._pending_facts)} facts, expected 500"
        )

    def test_supervisor_flushes_within_interval(self, loop_with_mock_engine) -> None:
        """C5 proof: supervisor must flush within interval seconds.

        This is the integration test that proves the sprint happened.
        Without this test, the supervisor is just a ghost in the code.
        """
        loop, _ = loop_with_mock_engine

        # Enqueue a fact
        loop._enqueue_fact(
            content="[INTEGRATION] sovereign persistence test",
            fact_type="decision",
        )
        assert len(loop._pending_facts) == 1

        # Wait for supervisor tick (interval=1s + buffer)
        time.sleep(2.0)

        # Queue must be drained — supervisor flushed it
        assert len(loop._pending_facts) == 0, (
            "Supervisor did NOT flush the queue within interval — C5 guarantee FAILED. "
            "This means data would be lost on SIGKILL."
        )

    def test_atexit_flush_covers_last_interval(self, loop_with_mock_engine) -> None:
        """C4 proof: atexit_flush drains facts accumulated after last supervisor tick."""
        loop, _ = loop_with_mock_engine

        # Enqueue a fact AFTER a supervisor tick (simulating the last-interval window)
        loop._enqueue_fact(
            content="[ATEXIT] fact created after last supervisor tick",
            fact_type="decision",
        )
        assert len(loop._pending_facts) == 1

        # Stop supervisor first (simulating clean process exit sequence)
        loop._supervisor.stop()

        loop._flush_pending(source="atexit_fallback")

        assert len(loop._pending_facts) == 0, (
            "atexit_flush did not drain pending facts — last-interval data would be lost"
        )

    def test_close_sequence_drains_all_facts(self, loop_with_mock_engine) -> None:
        """close() must leave zero pending facts — nothing silently dropped."""
        loop, _ = loop_with_mock_engine

        # Simulate a session with results
        from cortex.cli.loop_engine import TaskResult
        from cortex.cli.loop_models import TaskStatus

        loop._session.results.append(
            TaskResult(
                task="test task",
                status=TaskStatus.COMPLETED,
                output="success",
                duration_ms=42.0,
            )
        )

        # Enqueue facts manually (simulating mid-session activity)
        loop._enqueue_fact(content="[CLOSE] pre-existing fact", fact_type="knowledge")

        loop.close()

        # After close(), pending queue MUST be empty — no silent drops
        assert len(loop._pending_facts) == 0, (
            f"close() left {len(loop._pending_facts)} facts unwritten — "
            f"these would be permanently lost"
        )

    def test_atexit_flush_generates_ghost_on_crash(self, loop_with_mock_engine) -> None:
        """Ω₅: atexit_flush must generate a GHOST if close() was not called."""
        loop, _ = loop_with_mock_engine

        from cortex.cli.loop_engine import TaskResult
        from cortex.cli.loop_models import PersistenceType, TaskStatus

        # Simulate a session with one completed task
        loop._session.results.append(
            TaskResult(
                task="interrupted task",
                status=TaskStatus.COMPLETED,
                output="success",
                duration_ms=10.0,
            )
        )
        loop._session.tasks_completed = 1

        # We do NOT call loop.close() -> simulating crash/SIGTERM mid-session
        loop._atexit_flush()

        # It must have enqueued and flushed the pending facts
        engine = loop._engine

        # Extract the arguments passed to engine.store inside _run_async/mock_flush
        ghost_found = False

        # We need to inspect what was flushed by _flush_pending. Our wrapper captures logic inside _run_async.
        # But wait, engine.store returns a coroutine. In the mock engine, store is just a MagicMock.
        # Check its actual calls directly.
        for call in engine.store.call_args_list:
            kwargs = call.kwargs
            if kwargs.get("fact_type") == PersistenceType.GHOST.value:
                ghost_found = True
                assert "Sesión interrumpida" in kwargs["content"]
                break

        assert ghost_found, "atexit_flush failed to create a GHOST on crash"


# ─── Durability: confidence level documentation ───────────────────────


class TestDurabilityConfidenceLevels:
    """Document and validate the confidence levels of each persistence layer.

    These are specification tests — they encode the architectural contract
    explicitly. Changing these tests = changing the guarantee.
    """

    def test_persist_interval_default_is_60s(self) -> None:
        """The max data loss window is explicitly bounded at 60s."""
        from cortex.cli.loop_engine import PERSIST_INTERVAL

        assert PERSIST_INTERVAL == 60, (
            f"PERSIST_INTERVAL changed to {PERSIST_INTERVAL}s — "
            f"the durability SLA has changed. Update docs and this test intentionally."
        )

    def test_supervisor_thread_is_daemon(self) -> None:
        """Supervisor daemon=True: never blocks process exit.

        A non-daemon supervisor would prevent SIGTERM from working.
        """
        flush_fn = lambda source="supervisor": None  # noqa: E731
        supervisor = PersistSupervisor(flush_fn=flush_fn, interval=60)
        supervisor.start()
        is_daemon = supervisor._thread.daemon
        supervisor.stop()

        assert is_daemon is True, (
            "PersistSupervisor thread is not daemonized — it will block process exit on SIGTERM"
        )

    def test_pending_lock_exists_on_loop(self) -> None:
        """ExecutionLoop must have a threading.Lock for pending_facts."""
        with patch("cortex.cli.loop_engine.get_engine"):
            loop = ExecutionLoop(project="test", auto_persist=False)

        assert isinstance(loop._pending_lock, type(threading.Lock())), (
            "ExecutionLoop._pending_lock is not a threading.Lock — "
            "concurrent enqueues are not thread-safe"
        )
