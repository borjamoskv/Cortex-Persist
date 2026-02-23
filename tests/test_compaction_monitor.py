"""Tests for cortex.daemon.sidecar.compaction_monitor.

Covers:
- MemorySnapshot properties (free_ratio, malloc_free_ratio, rss_mb)
- MemoryPressureAlert message format
- MemoryPressureMonitor lifecycle (start/stop, idempotency)
- sample() one-shot coroutine
- No pressure → no alerts dispatched
- System free pressure → alert fired
- malloc free pressure → alert fired (Linux path)
- malloc_trim called when alerts exist
- legion import failure → WARNING (not crash)
- Backward-compat alias AsyncCompactionMonitor
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from cortex.daemon.sidecar.compaction_monitor import (
    AsyncCompactionMonitor,  # backward-compat alias
    MemoryPressureAlert,
    MemoryPressureMonitor,
    MemorySnapshot,
)
from cortex.daemon.sidecar.compaction_monitor import monitor as _mod

# ─── MemorySnapshot ───────────────────────────────────────────────────────────


class TestMemorySnapshot:
    def test_free_ratio_healthy(self):
        snap = MemorySnapshot(
            system_available_bytes=7_000_000_000, system_total_bytes=16_000_000_000
        )
        assert snap.free_ratio == pytest.approx(7 / 16, rel=1e-3)

    def test_free_ratio_no_data_returns_safe_default(self):
        assert MemorySnapshot().free_ratio == 1.0

    def test_malloc_free_ratio_linux(self):
        snap = MemorySnapshot(malloc_arena_bytes=1_000_000, malloc_free_bytes=200_000)
        assert snap.malloc_free_ratio == pytest.approx(0.2, rel=1e-3)

    def test_malloc_free_ratio_non_linux_returns_safe_default(self):
        assert MemorySnapshot(malloc_arena_bytes=0).malloc_free_ratio == 1.0

    def test_rss_mb(self):
        snap = MemorySnapshot(rss_bytes=104_857_600)  # 100 MB
        assert snap.rss_mb == pytest.approx(100.0, rel=1e-3)

    def test_immutable(self):
        snap = MemorySnapshot(rss_bytes=1)
        with pytest.raises((AttributeError, TypeError)):
            snap.rss_bytes = 2  # type: ignore[misc]


# ─── MemoryPressureAlert ──────────────────────────────────────────────────────


class TestMemoryPressureAlert:
    def _snap(self, *, sys_pct: float = 0.5, malloc_pct: float = 0.5) -> MemorySnapshot:
        total = 16_000_000_000
        return MemorySnapshot(
            system_available_bytes=int(total * sys_pct),
            system_total_bytes=total,
            malloc_arena_bytes=1_000_000,
            malloc_free_bytes=int(1_000_000 * malloc_pct),
            rss_bytes=200 * 1_048_576,
        )

    def test_message_contains_threshold_name(self):
        alert = MemoryPressureAlert(reason="low", snapshot=self._snap(), threshold_name="sys_free")
        assert "sys_free" in alert.message

    def test_message_contains_rss(self):
        alert = MemoryPressureAlert(reason="low", snapshot=self._snap(), threshold_name="t")
        assert "200.0MB" in alert.message

    def test_message_contains_ratios(self):
        alert = MemoryPressureAlert(
            reason="low", snapshot=self._snap(sys_pct=0.10, malloc_pct=0.05), threshold_name="t"
        )
        assert "10.0%" in alert.message  # sys_free ratio
        assert "5.0%" in alert.message  # malloc_free ratio


# ─── Backward-compat alias ────────────────────────────────────────────────────


def test_async_compaction_monitor_alias():
    assert AsyncCompactionMonitor is MemoryPressureMonitor


# ─── MemoryPressureMonitor lifecycle ─────────────────────────────────────────


class TestMemoryPressureMonitorLifecycle:
    def _make(self, **kw) -> MemoryPressureMonitor:
        return MemoryPressureMonitor(interval=0.05, **kw)

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        mon = self._make()
        loop = asyncio.get_running_loop()
        try:
            mon.start(loop=loop)
            assert mon._running is True
        finally:
            await mon.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running(self):
        mon = self._make()
        loop = asyncio.get_running_loop()
        try:
            mon.start(loop=loop)
            await mon.stop()
            assert mon._running is False
        finally:
            pass

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self):
        mon = self._make()
        loop = asyncio.get_running_loop()
        try:
            mon.start(loop=loop)
            task1 = mon._task
            mon.start(loop=loop)
            assert mon._task is task1  # same task, no duplicate
        finally:
            await mon.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self):
        mon = self._make()
        await mon.stop()  # must not raise


# ─── sample() ────────────────────────────────────────────────────────────────


class TestSample:
    @pytest.mark.asyncio
    async def test_sample_returns_snapshot(self):
        mon = MemoryPressureMonitor(interval=60.0)
        try:
            snap = await mon.sample()
            assert isinstance(snap, MemorySnapshot)
        finally:
            await mon.stop()


# ─── _tick pressure detection ────────────────────────────────────────────────


def _make_executor_mock(snapshot: MemorySnapshot, trim_result: bool = False) -> AsyncMock:
    """Return a coroutine side_effect that returns snapshot on first call, trim_result on second."""
    calls = []

    async def _side_effect(_exec, fn, *args):
        calls.append(fn)
        if fn is _mod._collect_snapshot:
            return snapshot
        return trim_result

    return _side_effect


class TestTickAlerts:
    def _healthy_snap(self) -> MemorySnapshot:
        return MemorySnapshot(
            system_available_bytes=8_000_000_000,
            system_total_bytes=16_000_000_000,
            malloc_arena_bytes=1_000_000,
            malloc_free_bytes=900_000,
        )

    def _low_sys_snap(self) -> MemorySnapshot:
        return MemorySnapshot(
            system_available_bytes=500_000_000,  # ~3% — below 15% default
            system_total_bytes=16_000_000_000,
        )

    def _low_malloc_snap(self) -> MemorySnapshot:
        return MemorySnapshot(
            system_available_bytes=8_000_000_000,
            system_total_bytes=16_000_000_000,
            malloc_arena_bytes=1_000_000,
            malloc_free_bytes=5_000,  # 0.5% — below 10% default
        )

    @pytest.mark.asyncio
    async def test_no_pressure_no_alert(self):
        dispatched: list[MemoryPressureAlert] = []

        async def _cb(a: MemoryPressureAlert) -> None:
            dispatched.append(a)

        mon = MemoryPressureMonitor(
            alert_callback=_cb, sys_free_threshold=0.10, malloc_free_threshold=0.05
        )
        loop = asyncio.get_running_loop()
        with patch.object(
            loop, "run_in_executor", side_effect=_make_executor_mock(self._healthy_snap())
        ):
            await mon._tick()

        assert dispatched == []

    @pytest.mark.asyncio
    async def test_sys_pressure_fires_alert(self):
        dispatched: list[MemoryPressureAlert] = []

        async def _cb(a: MemoryPressureAlert) -> None:
            dispatched.append(a)

        mon = MemoryPressureMonitor(alert_callback=_cb)
        loop = asyncio.get_running_loop()
        with patch.object(
            loop, "run_in_executor", side_effect=_make_executor_mock(self._low_sys_snap())
        ):
            await mon._tick()

        assert len(dispatched) >= 1
        assert dispatched[0].threshold_name == "sys_free"

    @pytest.mark.asyncio
    async def test_malloc_pressure_fires_alert(self):
        dispatched: list[MemoryPressureAlert] = []

        async def _cb(a: MemoryPressureAlert) -> None:
            dispatched.append(a)

        mon = MemoryPressureMonitor(alert_callback=_cb, malloc_free_threshold=0.10)
        loop = asyncio.get_running_loop()
        with patch.object(
            loop, "run_in_executor", side_effect=_make_executor_mock(self._low_malloc_snap())
        ):
            await mon._tick()

        malloc_alerts = [a for a in dispatched if a.threshold_name == "malloc_free"]
        assert len(malloc_alerts) >= 1

    @pytest.mark.asyncio
    async def test_malloc_trim_called_on_pressure(self):
        trim_called = []

        async def _executor_side(_exec, fn, *args):
            trim_called.append(fn.__name__)
            if fn is _mod._collect_snapshot:
                return self._low_sys_snap()
            return False  # _do_malloc_trim

        mon = MemoryPressureMonitor()
        loop = asyncio.get_running_loop()
        with patch.object(loop, "run_in_executor", side_effect=_executor_side):
            await mon._tick()

        assert "_do_malloc_trim" in trim_called


# ─── legion failure → WARNING ─────────────────────────────────────────────────


class TestLegionDispatch:
    @pytest.mark.asyncio
    async def test_legion_import_error_logs_warning(self, caplog):
        import logging

        mon = MemoryPressureMonitor(use_legion=True)
        snap = MemorySnapshot()
        alert = MemoryPressureAlert(reason="test", snapshot=snap, threshold_name="t")

        with patch.dict("sys.modules", {"legion": None}):
            with caplog.at_level(logging.WARNING, logger="compaction-sidecar"):
                await mon._dispatch(alert)

        assert any(
            "legion" in r.message.lower() for r in caplog.records if r.levelno == logging.WARNING
        )
