"""Tests — cortex.moltbook.preflight

Coverage:
    - Tier-0 (cache-only) BLOCKED when _suspended_until is in the future
    - Tier-0 CLEAR when _suspended_until has expired
    - Tier-1 (force_probe) BLOCKED from API response
    - Tier-1 (force_probe) CLEAR from API response
    - Tier-1 fails gracefully (fail-open) when /agents/status errors
    - session_preflight() raises SystemExit when suspended
    - session_preflight() returns PreflightResult when clear
    - require_clear_preflight decorator aborts when suspended, passes through when clear
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from cortex.moltbook.preflight import (
    PreflightResult,
    preflight_check,
    require_clear_preflight,
    session_preflight,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_client(
    *,
    suspended_until: float = 0.0,
    suspended_reason: str = "",
) -> MagicMock:
    """Return a minimal MoltbookClient mock with suspension state."""
    client = MagicMock()
    client._suspended_until = suspended_until
    client._suspended_reason = suspended_reason
    return client


# ─── Tier-0 (cache) tests ─────────────────────────────────────────────────────

class TestPreflightCacheTier:
    def test_blocked_when_cache_suspended(self) -> None:
        """Cache hit: suspended_until is in the future → BLOCKED immediately."""
        client = _make_client(
            suspended_until=time.time() + 3_600,
            suspended_reason="duplicate_comment",
        )
        result = preflight_check(client)

        assert result.clear is False
        assert result.suspended is True
        assert result.remaining_s > 0
        assert result.reason == "duplicate_comment"
        assert result.source == "cache"
        assert result.latency_ms >= 0

    def test_clear_when_cache_expired(self) -> None:
        """Cache miss: suspended_until is in the past → CLEAR with zero network."""
        client = _make_client(suspended_until=time.time() - 1.0)
        result = preflight_check(client)

        assert result.clear is True
        assert result.suspended is False
        assert result.source == "cache"

    def test_str_blocked(self) -> None:
        result = PreflightResult(
            clear=False,
            suspended=True,
            remaining_s=3600,
            reason="spam",
            source="cache",
            latency_ms=0.3,
        )
        assert "PREFLIGHT BLOCKED" in str(result)
        assert "3600s" in str(result)

    def test_str_clear(self) -> None:
        result = PreflightResult(clear=True, source="cache", latency_ms=0.1)
        assert "PREFLIGHT CLEAR" in str(result)


# ─── Tier-1 (force_probe) tests ───────────────────────────────────────────────

class TestPreflightProbeTier:
    def test_probe_blocked_from_api(self) -> None:
        """Live probe returns suspended flag → BLOCKED, cache is synced."""
        client = _make_client()  # Clean cache
        client.check_status.return_value = {
            "suspended": True,
            "suspended_until": "2099-12-31T23:59:59Z",
            "suspension_reason": "rate_abuse",
        }

        result = preflight_check(client, force_probe=True)

        assert result.clear is False
        assert result.suspended is True
        assert result.source == "api"
        assert result.reason == "rate_abuse"
        # Cache should now be updated
        assert client._suspended_until > time.time()

    def test_probe_clear_from_api(self) -> None:
        """Live probe returns no suspension → CLEAR."""
        client = _make_client()
        client.check_status.return_value = {"suspended": False}

        result = preflight_check(client, force_probe=True)

        assert result.clear is True
        assert result.source == "api"

    def test_probe_fails_gracefully_fail_open(self) -> None:
        """When /agents/status raises, default to CLEAR (fail-open)."""
        client = _make_client()
        client.check_status.side_effect = ConnectionError("network unreachable")

        result = preflight_check(client, force_probe=True)

        # Fail-open: let downstream circuit-breaker catch the real 403
        assert result.clear is True
        assert result.source == "error"
        assert "network unreachable" in result.meta.get("probe_error", "")

    def test_probe_skipped_when_cache_blocked(self) -> None:
        """If cache is already blocked, probe is NOT called (pure O(1) path)."""
        client = _make_client(suspended_until=time.time() + 100)

        result = preflight_check(client, force_probe=True)

        assert result.clear is False
        assert result.source == "cache"
        client.check_status.assert_not_called()


# ─── session_preflight ────────────────────────────────────────────────────────

class TestSessionPreflight:
    def test_raises_system_exit_when_suspended(self) -> None:
        client = _make_client(
            suspended_until=time.time() + 7_200,
            suspended_reason="auto-mod: spam",
        )
        with pytest.raises(SystemExit) as exc_info:
            session_preflight(client)
        assert "suspended" in str(exc_info.value).lower()
        assert "Zero tokens burned" in str(exc_info.value)

    def test_returns_result_when_clear(self) -> None:
        client = _make_client()
        client.check_status.return_value = {"suspended": False}

        result = session_preflight(client)

        assert isinstance(result, PreflightResult)
        assert result.clear is True


# ─── require_clear_preflight decorator ───────────────────────────────────────

class TestRequireClearPreflightDecorator:
    @pytest.mark.asyncio
    async def test_aborts_when_suspended(self) -> None:
        """Decorated coroutine never executes body when preflight is blocked."""
        call_log: list[str] = []

        @require_clear_preflight(client_attr="client")
        async def dispatch(client: object, llm: object, text: str) -> str:
            call_log.append(text)
            return text

        suspended_client = _make_client(suspended_until=time.time() + 999)
        result = await dispatch(client=suspended_client, llm=None, text="payload")

        assert result is None
        assert call_log == [], "LLM payload was never generated"

    @pytest.mark.asyncio
    async def test_passes_through_when_clear(self) -> None:
        """Decorated coroutine executes normally when preflight is clear."""
        @require_clear_preflight(client_attr="client")
        async def dispatch(client: object, llm: object, text: str) -> str:
            return f"dispatched:{text}"

        clear_client = _make_client()
        result = await dispatch(client=clear_client, llm=None, text="hello")

        assert result == "dispatched:hello"

    @pytest.mark.asyncio
    async def test_positional_client_resolution(self) -> None:
        """Decorator resolves client from positional args when not in kwargs."""
        @require_clear_preflight(client_attr="client")
        async def dispatch(client: object, text: str) -> str:
            return "ok"

        suspended_client = _make_client(suspended_until=time.time() + 500)
        result = await dispatch(suspended_client, "payload")

        assert result is None
