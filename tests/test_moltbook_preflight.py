"""Tests for Moltbook Preflight — the zero-waste dispatch gate (Ω₃)."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from moltbook.preflight import preflight_check, session_preflight


def _make_stub_client(suspended_until: float = 0.0, suspended_reason: str = ""):
    """Create a minimal MoltbookClient stub with suspension state."""
    client = MagicMock()
    client._suspended_until = suspended_until
    client._suspended_reason = suspended_reason
    client.check_status = AsyncMock(return_value={"suspended": False})
    return client


class TestPreflightCheck:
    """Test the pre-flight suspension gate."""

    @pytest.mark.asyncio
    async def test_clear_when_not_suspended(self):
        client = _make_stub_client(suspended_until=0.0)
        result = await preflight_check(client)
        assert result.clear is True
        assert result.source == "cache"
        assert result.suspended is False

    @pytest.mark.asyncio
    async def test_blocked_from_cache(self):
        future = time.time() + 300  # 5 minutes from now
        client = _make_stub_client(suspended_until=future, suspended_reason="spam detected")
        result = await preflight_check(client)
        assert result.clear is False
        assert result.suspended is True
        assert result.remaining_s > 0
        assert "spam" in result.reason

    @pytest.mark.asyncio
    async def test_forced_probe_live_clear(self):
        client = _make_stub_client()
        client.check_status = AsyncMock(return_value={"suspended": False})
        result = await preflight_check(client, force_probe=True)
        assert result.clear is True
        assert result.source == "api"
        client.check_status.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_session_preflight_raises_on_suspend(self):
        future = time.time() + 600
        client = _make_stub_client(suspended_until=future, suspended_reason="auto-mod")
        # session_preflight does force_probe but cache blocks first
        with pytest.raises(SystemExit, match="suspended"):
            await session_preflight(client)
