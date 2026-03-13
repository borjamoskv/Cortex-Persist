"""Tests for cortex.immune.error_boundary — Ω₅ Antifragile Decorator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.immune.error_boundary import ErrorBoundary, error_boundary

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_pipeline():
    """Reset singleton pipeline between tests."""
    with (
        patch(
            "cortex.immune.error_boundary.ErrorBoundary._persist",
            new_callable=AsyncMock,
            return_value=42,
        ) as mock_persist,
        patch(
            "cortex.immune.error_boundary.ErrorBoundary._persist_sync",
            new_callable=MagicMock,
        ) as mock_persist_sync,
    ):
        yield mock_persist, mock_persist_sync


# ── Async Context Manager Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_async_cm_captures_error(_reset_pipeline):
    """ErrorBoundary captures errors and persists as ghost."""
    mock_persist, _ = _reset_pipeline

    with pytest.raises(ValueError, match="test error"):
        async with ErrorBoundary("test.module"):
            raise ValueError("test error")

    mock_persist.assert_called_once()
    error_arg = mock_persist.call_args[0][0]
    assert isinstance(error_arg, ValueError)
    assert str(error_arg) == "test error"


@pytest.mark.asyncio
async def test_async_cm_no_error_no_persist(_reset_pipeline):
    """No error → no ghost persisted."""
    mock_persist, _ = _reset_pipeline

    async with ErrorBoundary("test.module"):
        result = 42

    mock_persist.assert_not_called()
    assert result == 42


@pytest.mark.asyncio
async def test_async_cm_reraise_false_swallows(_reset_pipeline):
    """With reraise=False, error is swallowed after persist."""
    mock_persist, _ = _reset_pipeline

    # Should NOT raise
    async with ErrorBoundary("test.daemon", reraise=False):
        raise RuntimeError("swallowed error")

    mock_persist.assert_called_once()


@pytest.mark.asyncio
async def test_async_cm_passes_through_cancelled_error(_reset_pipeline):
    """CancelledError must propagate — never captured."""
    mock_persist, _ = _reset_pipeline

    with pytest.raises(asyncio.CancelledError):
        async with ErrorBoundary("test.module"):
            raise asyncio.CancelledError()

    mock_persist.assert_not_called()


@pytest.mark.asyncio
async def test_async_cm_passes_through_keyboard_interrupt(_reset_pipeline):
    """KeyboardInterrupt must propagate — never captured."""
    mock_persist, _ = _reset_pipeline

    with pytest.raises(KeyboardInterrupt):
        async with ErrorBoundary("test.module"):
            raise KeyboardInterrupt()

    mock_persist.assert_not_called()


# ── Sync Context Manager Tests ────────────────────────────────────────


def test_sync_cm_captures_error(_reset_pipeline):
    """Sync context manager captures and persists errors."""
    _, mock_persist_sync = _reset_pipeline

    with pytest.raises(ValueError, match="sync error"):
        with ErrorBoundary("test.sync_module"):
            raise ValueError("sync error")

    mock_persist_sync.assert_called_once()


def test_sync_cm_reraise_false(_reset_pipeline):
    """Sync context manager with reraise=False swallows."""
    _, mock_persist_sync = _reset_pipeline

    with ErrorBoundary("test.sync_daemon", reraise=False):
        raise RuntimeError("swallowed sync")

    mock_persist_sync.assert_called_once()


# ── Decorator Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_decorator_captures(_reset_pipeline):
    """Async decorator captures errors from decorated function."""
    mock_persist, _ = _reset_pipeline

    @error_boundary("test.async_func")
    async def failing_func():
        raise TypeError("decorated failure")

    with pytest.raises(TypeError, match="decorated failure"):
        await failing_func()

    mock_persist.assert_called_once()


@pytest.mark.asyncio
async def test_async_decorator_reraise_false(_reset_pipeline):
    """Async decorator with reraise=False returns None on error."""
    mock_persist, _ = _reset_pipeline

    @error_boundary("test.daemon_func", reraise=False)
    async def daemon_cycle():
        raise RuntimeError("cycle failure")

    result = await daemon_cycle()
    assert result is None
    mock_persist.assert_called_once()


def test_sync_decorator_captures(_reset_pipeline):
    """Sync decorator captures errors from decorated function."""
    _, mock_persist_sync = _reset_pipeline

    @error_boundary("test.sync_func")
    def failing_sync():
        raise OSError("sync decorated failure")

    with pytest.raises(OSError, match="sync decorated failure"):
        failing_sync()

    mock_persist_sync.assert_called_once()


@pytest.mark.asyncio
async def test_decorator_preserves_return(_reset_pipeline):
    """Decorator preserves return value when no error occurs."""
    mock_persist, _ = _reset_pipeline

    @error_boundary("test.happy_path")
    async def healthy_func(x: int) -> int:
        return x * 2

    assert await healthy_func(21) == 42
    mock_persist.assert_not_called()


@pytest.mark.asyncio
async def test_decorator_preserves_functools_wraps(_reset_pipeline):
    """Decorator preserves function name and docstring."""

    @error_boundary("test.meta")
    async def well_documented():
        """Important docstring."""

    assert well_documented.__name__ == "well_documented"
    assert well_documented.__doc__ == "Important docstring."


# ── Edge Cases ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extra_meta_passed(_reset_pipeline):
    """Extra metadata is passed through to boundary."""
    boundary = ErrorBoundary(
        "test.meta",
        extra_meta={"custom_key": "custom_value"},
    )
    assert boundary._extra_meta == {"custom_key": "custom_value"}


@pytest.mark.asyncio
async def test_project_customization(_reset_pipeline):
    """Custom project is stored on boundary."""
    boundary = ErrorBoundary("test.custom", project="MY_PROJECT")
    assert boundary._project == "MY_PROJECT"
