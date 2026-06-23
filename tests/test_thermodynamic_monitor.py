# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import asyncio

import pytest

from babylon60.extensions.daemon.monitors.thermodynamic import ThermodynamicMemoryMonitor


class _Manager:
    _l2: object = object()


class _FakePruner:
    def __init__(self, calls: list[str], *_args, **_kwargs) -> None:
        self._calls = calls

    async def prune_cycle(self, tenant_id: str) -> int:
        self._calls.append(tenant_id)
        return 2


def _pruner_factory(calls: list[str]):
    def _factory(*args, **kwargs):
        return _FakePruner(calls, *args, **kwargs)

    return _factory


class _FailingPruner:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def prune_cycle(self, tenant_id: str) -> int:
        raise ValueError("boom")


@pytest.mark.parametrize("interval_seconds", [0])
def test_check_succeeds_sync_without_event_loop(monkeypatch, interval_seconds: int):
    calls: list[str] = []
    monkeypatch.setattr(
        "babylon60.extensions.daemon.monitors.thermodynamic.EntropyPruner",
        _pruner_factory(calls),
    )

    monitor = ThermodynamicMemoryMonitor(
        manager=_Manager(),
        tenants=["tenant-a"],
        interval_seconds=interval_seconds,
    )

    alerts = monitor.check()

    assert calls == ["tenant-a"]
    assert len(alerts) == 1
    assert alerts[0].tenant_id == "tenant-a"
    assert alerts[0].pruned_count == 2


@pytest.mark.asyncio
async def test_check_schedules_in_running_loop(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "babylon60.extensions.daemon.monitors.thermodynamic.EntropyPruner",
        _pruner_factory(calls),
    )

    monitor = ThermodynamicMemoryMonitor(
        manager=_Manager(),
        tenants=["tenant-a"],
        interval_seconds=0,
    )

    alerts = monitor.check()

    assert alerts == []
    await asyncio.sleep(0)
    assert calls == ["tenant-a"]


def test_check_async_swallow_known_errors(monkeypatch):
    monkeypatch.setattr(
        "babylon60.extensions.daemon.monitors.thermodynamic.EntropyPruner",
        _FailingPruner,
    )

    monitor = ThermodynamicMemoryMonitor(
        manager=_Manager(),
        tenants=["tenant-a"],
        interval_seconds=0,
    )

    alerts = monitor.check()
    assert alerts == []
