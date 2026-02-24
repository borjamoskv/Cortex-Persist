"""Tests for cortex.event_loop — Sovereign Event Loop with uvloop."""

from __future__ import annotations

import asyncio

import pytest

from cortex.events.loop import get_loop_info, install_uvloop, sovereign_run


class TestInstallUvloop:
    def test_returns_true_when_available(self):
        # uvloop is installed in this venv
        result = install_uvloop()
        assert result is True

    def test_idempotent(self):
        assert install_uvloop() is True
        assert install_uvloop() is True  # Second call still True


class TestSovereignRun:
    def test_runs_coroutine(self):
        async def double(x: int) -> int:
            return x * 2

        result = sovereign_run(double(21))
        assert result == 42

    def test_runs_async_sleep(self):
        async def sleeper():
            await asyncio.sleep(0.01)
            return "awake"

        assert sovereign_run(sleeper()) == "awake"

    def test_exception_propagation(self):
        async def fail():
            raise ValueError("sovereign fail")

        with pytest.raises(ValueError, match="sovereign fail"):
            sovereign_run(fail())


class TestGetLoopInfo:
    def test_info_keys(self):
        info = get_loop_info()
        assert "uvloop_installed" in info
        assert "python_version" in info
        assert "platform" in info

    def test_no_running_loop(self):
        info = get_loop_info()
        assert info["loop_running"] is False
