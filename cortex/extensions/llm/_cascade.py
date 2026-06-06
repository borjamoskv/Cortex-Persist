# [C5-REAL] Exergy-Maximized
"""Cascade Manager.

Resilient transition and grouping for LLM providers.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from cortex.extensions.llm._models import CascadeTier, IntentProfile

if TYPE_CHECKING:
    from cortex.extensions.llm._models import BaseProvider

logger = logging.getLogger("cortex.extensions.llm.cascade")


def classify_tier(provider: BaseProvider, intent: IntentProfile) -> CascadeTier:
    """Classify which cascade tier a fallback belongs to."""
    if provider.intent_affinity == intent:
        return CascadeTier.TYPED_MATCH
    return CascadeTier.SAFETY_NET


class CascadeManager:
    """Track provider health and routing state (NXDOMAIN/A-record caching/KV-affinity)."""

    def __init__(self, negative_ttl: float = 300.0, positive_ttl: float = 600.0):
        self.negative_ttl = negative_ttl
        self.positive_ttl = positive_ttl
        # provider_name -> timestamp of failure
        self._nxdomain_cache: dict[str, float] = {}
        # provider_name -> consecutive failures (thermodynamic decay)
        self._nxdomain_failures: dict[str, int] = {}
        # provider_name -> (timestamp, latency)
        self._a_records: dict[str, tuple[float, float]] = {}
        # prefix_hash -> {provider_name: timestamp}
        self._kv_affinity: dict[str, dict[str, float]] = {}

    def set_nx_record(self, provider_name: str) -> None:
        """Cache a provider failure (NXDOMAIN) with thermodynamic decay."""
        self._nxdomain_cache[provider_name] = time.monotonic()
        self._nxdomain_failures[provider_name] = self._nxdomain_failures.get(provider_name, 0) + 1

    def set_a_record(self, provider_name: str, latency_ms: float) -> None:
        """Cache a provider success (A-record) and reset decay."""
        self._a_records[provider_name] = (time.monotonic(), latency_ms)
        self._nxdomain_failures.pop(provider_name, None)

    def set_kv_affinity(self, provider_name: str, prefix_hash: str) -> None:
        """Mark that a provider has cached a specific context prefix."""
        if prefix_hash not in self._kv_affinity:
            self._kv_affinity[prefix_hash] = {}
        self._kv_affinity[prefix_hash][provider_name] = time.monotonic()

    def get_a_record(self, provider_name: str) -> tuple[float, float] | None:
        """Get success record if within TTL."""
        record = self._a_records.get(provider_name)
        if record and (time.monotonic() - record[0]) < self.positive_ttl:
            return record
        return None

    def is_nxdomain_cached(self, provider_name: str) -> bool:
        """True if provider is currently circuit-broken."""
        nx_at = self._nxdomain_cache.get(provider_name)
        if nx_at:
            failures = self._nxdomain_failures.get(provider_name, 1)
            # Thermodynamic decay: exponential backoff based on consecutive failures
            effective_ttl = self.negative_ttl * (2 ** (failures - 1))
            if (time.monotonic() - nx_at) < effective_ttl:
                return True
        return False

    def promote_known_good(
        self,
        providers: list[BaseProvider],
        intent: IntentProfile,
        prefix_hash: str | None = None,
    ) -> list[BaseProvider]:
        """Within a tier, promote KV-affinity and A-record cached providers."""
        affinity_providers = []
        if prefix_hash and prefix_hash in self._kv_affinity:
            affinity_providers = list(self._kv_affinity[prefix_hash].keys())

        # Sort: KV Affinity -> Low Latency -> Unknown
        with_affinity: list[tuple[BaseProvider, float]] = []
        known_good: list[tuple[BaseProvider, float]] = []
        unknown: list[BaseProvider] = []

        for p in providers:
            record = self.get_a_record(p.provider_name)
            latency = record[1] if record else float("inf")

            if p.provider_name in affinity_providers:
                with_affinity.append((p, latency))
            elif record:
                known_good.append((p, latency))
            else:
                unknown.append(p)

        with_affinity.sort(key=lambda x: x[1])
        known_good.sort(key=lambda x: x[1])

        return [p for p, _ in with_affinity] + [p for p, _ in known_good] + unknown
