# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX LLM Router — DNS-Inspired Resolver Caches.

NegativeCache (RFC 2308 NXDOMAIN) — failed provider suppression.
PositiveCache (DNS A-record) — successful provider promotion.

Extraído de router.py (Ω₂ Landauer split).
"""

from __future__ import annotations

import logging
import time

__all__ = ["NegativeCache", "PositiveCache"]

logger = logging.getLogger("cortex.llm.cache")


# ─── Negative Cache (RFC 2308) ─────────────────────────────────────────────


class NegativeCache:
    """RFC 2308 NXDOMAIN cache for failed providers.

    When a provider fails for a specific intent, cache the failure with a TTL
    so subsequent calls skip it entirely. Converts the fallback cascade from
    reactive (try → fail → retry next call) to predictive (known-dead → skip).

    Key: (provider_name, intent_value) — scoped per intent, not global.
    A provider that fails for CODE may still be healthy for REASONING.

    Axiom: Ω₅ (Antifragile by Default) — the failure feeds the system.
    """

    __slots__ = ("_entries", "_default_ttl")

    def __init__(self, default_ttl: float = 300.0) -> None:
        self._entries: dict[tuple[str, str], float] = {}
        self._default_ttl = default_ttl  # 5 min default

    def record_failure(
        self, provider_name: str, intent: str, ttl: float | None = None
    ) -> None:
        """NXDOMAIN — cache that this provider failed for this intent."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expiry = time.monotonic() + effective_ttl
        self._entries[(provider_name, intent)] = expiry
        logger.debug(
            "NXDOMAIN cached: %s for intent=%s (TTL=%.0fs)",
            provider_name,
            intent,
            effective_ttl,
        )

    def is_suppressed(self, provider_name: str, intent: str) -> bool:
        """Check if provider is in the NXDOMAIN cache (still within TTL)."""
        key = (provider_name, intent)
        expiry = self._entries.get(key)
        if expiry is None:
            return False
        if time.monotonic() >= expiry:
            del self._entries[key]  # TTL expired — resurrect
            logger.debug(
                "NXDOMAIN expired: %s resurrected for intent=%s",
                provider_name,
                intent,
            )
            return False
        return True

    def clear(self) -> None:
        """Flush all negative cache entries."""
        self._entries.clear()

    @property
    def suppressed_count(self) -> int:
        """Active suppressions count (for observability)."""
        return len(self._entries)


class PositiveCache:
    """DNS A-Record cache for successful providers.

    Symmetric counterpart to NegativeCache (NXDOMAIN).
    Key: (provider_name, intent_value) — scoped per intent.
    Value: (expiry_timestamp, latency_ms).

    Providers with a fresh A-record get promoted in the cascade
    ordering via ``known_good_providers(intent)``. Among known-good
    providers, faster ones (lower latency) come first.

    TTL default = 600s (10 min) — 2x longer than NXDOMAIN, matching
    typical DNS behavior: positive evidence is more durable than negative.

    Axiom: Ω₅ (Antifragile by Default) — success feeds the system.
    """

    __slots__ = ("_entries", "_default_ttl")

    def __init__(self, default_ttl: float = 600.0) -> None:
        self._entries: dict[tuple[str, str], tuple[float, float]] = {}
        self._default_ttl = default_ttl  # 10 min default

    def record_success(
        self,
        provider_name: str,
        intent: str,
        latency_ms: float,
        ttl: float | None = None,
    ) -> None:
        """A-record — cache that this provider succeeded for this intent."""
        expiry = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        self._entries[(provider_name, intent)] = (expiry, latency_ms)
        logger.debug(
            "A-record cached: %s for intent=%s (%.1fms, TTL=%.0fs)",
            provider_name,
            intent,
            latency_ms,
            ttl if ttl is not None else self._default_ttl,
        )

    def is_known_good(self, provider_name: str, intent: str) -> bool:
        """Check if provider has a valid A-record for this intent."""
        key = (provider_name, intent)
        entry = self._entries.get(key)
        if entry is None:
            return False
        expiry, _ = entry
        if time.monotonic() >= expiry:
            del self._entries[key]  # TTL expired
            return False
        return True

    def get_latency(self, provider_name: str, intent: str) -> float | None:
        """Get cached latency for a known-good provider, or None."""
        key = (provider_name, intent)
        entry = self._entries.get(key)
        if entry is None:
            return None
        expiry, latency_ms = entry
        if time.monotonic() >= expiry:
            del self._entries[key]
            return None
        return latency_ms

    def known_good_providers(self, intent: str) -> list[tuple[str, float]]:
        """Return all known-good providers for an intent, sorted by latency.

        Returns list of (provider_name, latency_ms) — fastest first.
        Expired entries are cleaned lazily during iteration.
        """
        now = time.monotonic()
        expired_keys: list[tuple[str, str]] = []
        good: list[tuple[str, float]] = []

        for (pname, pintent), (expiry, latency) in self._entries.items():
            if pintent != intent:
                continue
            if now >= expiry:
                expired_keys.append((pname, pintent))
                continue
            good.append((pname, latency))

        # Lazy cleanup
        for key in expired_keys:
            del self._entries[key]

        # Sort by latency — fastest first
        good.sort(key=lambda x: x[1])
        return good

    def clear(self) -> None:
        """Flush all positive cache entries."""
        self._entries.clear()

    @property
    def cached_count(self) -> int:
        """Active A-record count (for observability)."""
        return len(self._entries)
