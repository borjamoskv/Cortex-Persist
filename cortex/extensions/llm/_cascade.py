"""CORTEX v5.0 — Cascade Manager.

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
    """Track provider health and routing state (NXDOMAIN/A-record caching)."""

    def __init__(self, negative_ttl: float = 300.0, positive_ttl: float = 600.0):
        self.negative_ttl = negative_ttl
        self.positive_ttl = positive_ttl
        # provider_name -> timestamp of failure
        self._nxdomain_cache: dict[str, float] = {}
        # provider_name -> (timestamp, latency)
        self._a_records: dict[str, tuple[float, float]] = {}

    def set_nx_record(self, provider_name: str) -> None:
        """Cache a provider failure (NXDOMAIN)."""
        self._nxdomain_cache[provider_name] = time.time()

    def set_a_record(self, provider_name: str, latency_ms: float) -> None:
        """Cache a provider success (A-record)."""
        self._a_records[provider_name] = (time.time(), latency_ms)

    def get_a_record(self, provider_name: str) -> tuple[float, float] | None:
        """Get success record if within TTL."""
        record = self._a_records.get(provider_name)
        if record and (time.time() - record[0]) < self.positive_ttl:
            return record
        return None

    def is_nxdomain_cached(self, provider_name: str) -> bool:
        """True if provider is currently circuit-broken."""
        nx_at = self._nxdomain_cache.get(provider_name)
        if nx_at and (time.time() - nx_at) < self.negative_ttl:
            return True
        return False

    def promote_known_good(
        self,
        providers: list[BaseProvider],
        intent: IntentProfile,
    ) -> list[BaseProvider]:
        """Within a tier, promote A-record cached providers to the front."""
        known_good: list[tuple[BaseProvider, float]] = []
        unknown: list[BaseProvider] = []

        for p in providers:
            record = self.get_a_record(p.provider_name)
            if record:
                known_good.append((p, record[1]))
            else:
                unknown.append(p)

        known_good.sort(key=lambda x: x[1])
        return [p for p, lat in known_good] + unknown
