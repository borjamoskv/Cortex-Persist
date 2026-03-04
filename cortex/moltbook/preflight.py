"""Moltbook Pre-flight Check — Zero-Waste Dispatch Gate.

Consult suspension state BEFORE generating any LLM payload.
If the destination is blocked, abort immediately: zero tokens burned.

Architecture:
    PreflightResult (dataclass) ← pure data, no side effects
    preflight_check()           ← consults client state + optionally fetches /agents/status
    dispatch_guard()            ← decorator / context-manager for dispatch functions

Race-condition handling:
    The circuit breaker may catch the 403 AFTER the first request, but
    the in-process _suspended_until cache is set immediately by _handle_403().
    preflight_check() reads that cache first (O(1), no network) and only
    makes a live /agents/status fetch when the cache shows clean but the
    caller requests a fresh probe (force_probe=True).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.moltbook.client import MoltbookClient

logger = logging.getLogger(__name__)


# ─── Result type ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PreflightResult:
    """Immutable result of a pre-flight suspension check.

    Attributes:
        clear:            True → safe to proceed with LLM generation + dispatch.
        suspended:        True → agent is under auto-mod suspension.
        remaining_s:      Seconds until suspension expires (0 if clear).
        reason:           Auto-mod reason string (empty if clear).
        source:           Where we got the status: 'cache' | 'api' | 'error'.
        latency_ms:       Time taken for the check in milliseconds.
    """

    clear: bool
    suspended: bool = False
    remaining_s: int = 0
    reason: str = ""
    source: str = "cache"
    latency_ms: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.clear:
            return f"✅ PREFLIGHT CLEAR [{self.source} +{self.latency_ms:.1f}ms]"
        return (
            f"🚫 PREFLIGHT BLOCKED [{self.source} +{self.latency_ms:.1f}ms] "
            f"suspended={self.remaining_s}s — {self.reason}"
        )


# ─── Core check ───────────────────────────────────────────────────────────────


async def preflight_check(
    client: MoltbookClient,
    *,
    force_probe: bool = False,
) -> PreflightResult:
    """Consult suspension state before generating LLM payloads.
    Refactored to be ASYNC.
    """
    t0 = time.perf_counter()

    # ── Tier 0: in-process cache ──────────────────────────────────────────────
    now = time.time()
    if now < client._suspended_until:
        remaining = int(client._suspended_until - now)
        elapsed_ms = (time.perf_counter() - t0) * 1_000
        result = PreflightResult(
            clear=False,
            suspended=True,
            remaining_s=remaining,
            reason=client._suspended_reason or "auto-mod suspension (cached)",
            source="cache",
            latency_ms=elapsed_ms,
        )
        logger.warning("PREFLIGHT [cache] BLOCKED — %ds remaining", remaining)
        return result

    # ── Tier 1: live API probe (opt-in) ──────────────────────────────────────
    if not force_probe:
        elapsed_ms = (time.perf_counter() - t0) * 1_000
        return PreflightResult(clear=True, source="cache", latency_ms=elapsed_ms)

    try:
        status_resp = await client.check_status()
        elapsed_ms = (time.perf_counter() - t0) * 1_000

        # Parse suspension fields — API may return various shapes
        suspended_flag: bool = status_resp.get("suspended", False)
        until_str: str = status_resp.get("suspended_until", "") or ""
        reason: str = status_resp.get("suspension_reason", "") or status_resp.get("reason", "")

        if suspended_flag or until_str:
            # Defensive: sync cache with reality
            if until_str:
                from datetime import datetime

                try:
                    until_dt = datetime.fromisoformat(until_str.replace("Z", "+00:00"))
                    client._suspended_until = until_dt.timestamp()
                except ValueError:
                    client._suspended_until = time.time() + 3_600  # 1h fallback

            client._suspended_reason = reason or "auto-mod (live probe)"
            remaining = int(max(0, client._suspended_until - time.time()))

            result = PreflightResult(
                clear=False,
                suspended=True,
                remaining_s=remaining,
                reason=client._suspended_reason,
                source="api",
                latency_ms=elapsed_ms,
                meta={"raw_status": status_resp},
            )
            logger.warning(
                "PREFLIGHT [api] BLOCKED — %ds remaining. Reason: %s",
                remaining,
                reason,
            )
            return result

        return PreflightResult(clear=True, source="api", latency_ms=elapsed_ms)

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1_000
        logger.error("PREFLIGHT probe failed (defaulting to CLEAR): %s", exc)
        return PreflightResult(
            clear=True,
            source="error",
            latency_ms=elapsed_ms,
            meta={"probe_error": str(exc)},
        )


async def session_preflight(client: MoltbookClient) -> PreflightResult:
    """Run a FULL preflight at session start (force_probe=True).
    Refactored to be ASYNC.
    """
    result = await preflight_check(client, force_probe=True)
    if result.suspended:
        logger.error(
            "SESSION ABORTED by pre-flight — agent suspended %ds. %s",
            result.remaining_s,
            result.reason,
        )
        raise SystemExit(
            f"🚫 Moltbook agent suspended for {result.remaining_s}s. "
            f"Reason: {result.reason}. Zero tokens burned."
        )
    logger.info("%s", result)
    return result
