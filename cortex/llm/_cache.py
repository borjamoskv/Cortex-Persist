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
from typing import Final

from cortex.database.tlru_cache import TLRUCache

__all__ = ["NegativeCache", "PositiveCache"]

logger = logging.getLogger("cortex.llm.cache")

_DEFAULT_NEG_CAPACITY: Final[int] = 1000
_DEFAULT_POS_CAPACITY: Final[int] = 5000


# ─── Negative Cache (RFC 2308) ─────────────────────────────────────────────


class NegativeCache:
    """RFC 2308 NXDOMAIN cache for failed providers using bounded TLRU.

    Axiom: Ω₅ (Antifragile by Default) — the failure feeds the system.
    Derivation: Ω₂ (Entropic Asymmetry) — bounded memory for failure states.
    """

    __slots__ = ("_cache",)

    def __init__(self, capacity: int = _DEFAULT_NEG_CAPACITY, default_ttl: float = 300.0) -> None:
        self._cache = TLRUCache(maxsize=capacity, ttl=default_ttl)

    def record_failure(self, provider_name: str, intent: str, ttl: float | None = None) -> None:
        """NXDOMAIN — cache that this provider failed for this intent."""
        key = f"{provider_name}:{intent}"
        # TLRUCache stores a value; we just store 1.0 as a placeholder since presence is what matters
        # If a custom TTL is provided, we can't easily override it per-item in the current TLRUCache
        # so we rely on the default_ttl set at init.
        self._cache[key] = 1.0
        logger.debug(
            "NXDOMAIN cached: %s for intent=%s",
            provider_name,
            intent,
        )

    def is_suppressed(self, provider_name: str, intent: str) -> bool:
        """Check if provider is in the NXDOMAIN cache (still within TTL)."""
        key = f"{provider_name}:{intent}"
        return key in self._cache

    def clear(self) -> None:
        """Flush all negative cache entries."""
        self._cache.clear()

    @property
    def suppressed_count(self) -> int:
        """Active suppressions count (for observability)."""
        return len(self._cache)


class PositiveCache:
    """DNS A-Record cache for successful providers using bounded TLRU.

    Axiom: Ω₅ (Antifragile by Default) — success feeds the system.
    """

    __slots__ = ("_cache",)

    def __init__(self, capacity: int = _DEFAULT_POS_CAPACITY, default_ttl: float = 600.0) -> None:
        self._cache = TLRUCache(maxsize=capacity, ttl=default_ttl)

    def record_success(
        self,
        provider_name: str,
        intent: str,
        latency_ms: float,
        ttl: float | None = None,
    ) -> None:
        """A-record — cache that this provider succeeded for this intent."""
        key = f"{provider_name}:{intent}"
        self._cache[key] = latency_ms
        logger.debug(
            "A-record cached: %s for intent=%s (%.1fms)",
            provider_name,
            intent,
            latency_ms,
        )

    def is_known_good(self, provider_name: str, intent: str) -> bool:
        """Check if provider has a valid A-record for this intent."""
        key = f"{provider_name}:{intent}"
        return key in self._cache

    def get_latency(self, provider_name: str, intent: str) -> float | None:
        """Get cached latency for a known-good provider, or None."""
        key = f"{provider_name}:{intent}"
        return self._cache.get(key)

    def known_good_providers(self, intent: str) -> list[tuple[str, float]]:
        """Return all known-good providers for an intent, sorted by latency.

        Returns list of (provider_name, latency_ms) — fastest first.
        """
        # TLRUCache doesn't expose internal items easily in a sorted way.
        # We access the internal OrderedDict for this specific use case.
        # Note: This is an architectural concession for the 'fastest first' requirement.
        now = time.monotonic()
        good: list[tuple[str, float]] = []

        # pylint: disable=protected-access
        for key, (ts, latency) in self._cache._cache.items():
            if ":" not in key:
                continue
            pname, pintent = key.split(":", 1)
            if pintent == intent and (now - ts <= self._cache.ttl):
                good.append((pname, latency))

        # Sort by latency — fastest first
        good.sort(key=lambda x: x[1])
        return good

    def clear(self) -> None:
        """Flush all positive cache entries."""
        self._cache.clear()

    @property
    def cached_count(self) -> int:
        """Active A-record count (for observability)."""
        return len(self._cache)
