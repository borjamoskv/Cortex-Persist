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
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from functools import wraps
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


def preflight_check(
    client: MoltbookClient,
    *,
    force_probe: bool = False,
) -> PreflightResult:
    """Consult suspension state before generating LLM payloads.

    Strategy (two-tier, latency-ordered):
        Tier 0 — in-process cache (O(1), zero network):
            Read client._suspended_until.
            If time.time() < _suspended_until → BLOCKED, return immediately.

        Tier 1 — live API probe (only when force_probe=True and cache is clean):
            Call GET /agents/status.
            Parse suspension fields from response.
            Update client cache if suspended (defensive sync).

    Args:
        client:       Active MoltbookClient instance.
        force_probe:  When True, makes a live /agents/status call even if the
                      in-process cache shows clean. Use at session start or after
                      a long idle period. Default False (cache-only, zero latency).

    Returns:
        PreflightResult — immutable verdict.
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
        status_resp = client.check_status()
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
        # Fail-open: if we can't probe, allow execution and let the dispatch
        # circuit-breaker catch the real 403.
        return PreflightResult(
            clear=True,
            source="error",
            latency_ms=elapsed_ms,
            meta={"probe_error": str(exc)},
        )


# ─── Decorator / guard ────────────────────────────────────────────────────────


def require_clear_preflight(
    client_attr: str = "client",
    force_probe: bool = False,
) -> Callable:
    """Decorator that aborts async dispatch functions when preflight fails.

    Usage:
        @require_clear_preflight(client_attr="client")
        async def process_post(self, client, llm, post):
            ...  # only runs if preflight is clear

        @require_clear_preflight()  # assumes first arg is 'client'
        async def dispatch(client, llm, ...):
            ...

    The decorated function returns None (silently) when blocked.
    """

    def decorator(
        fn: Callable[..., Coroutine[Any, Any, Any]],
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Resolve client from args or kwargs
            resolved_client: MoltbookClient | None = kwargs.get(client_attr)
            if resolved_client is None:
                # Try positional: first arg named 'client'
                import inspect

                sig = inspect.signature(fn)
                params = list(sig.parameters.keys())
                if client_attr in params:
                    idx = params.index(client_attr)
                    if idx < len(args):
                        resolved_client = args[idx]

            if resolved_client is None:
                logger.warning("PREFLIGHT: could not resolve client, proceeding without check.")
                return await fn(*args, **kwargs)

            result = preflight_check(resolved_client, force_probe=force_probe)
            logger.debug("%s", result)

            if not result.clear:
                logger.warning(
                    "PREFLIGHT aborted '%s' — %s",
                    fn.__qualname__,
                    result,
                )
                return None  # Zero tokens burned

            return await fn(*args, **kwargs)

        return wrapper

    return decorator


# ─── Session-start helper ─────────────────────────────────────────────────────


def session_preflight(client: MoltbookClient) -> PreflightResult:
    """Run a FULL preflight at session start (force_probe=True).

    Call this once in main() before entering the dispatch loop.
    Raises SystemExit if suspended, so the caller never reaches LLM init.

    Example:
        async def main():
            client = MoltbookClient()
            session_preflight(client)   # exits here if blocked
            llm = SovereignLLM()        # only instantiated if clear
            ...
    """
    result = preflight_check(client, force_probe=True)
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
