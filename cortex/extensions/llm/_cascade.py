from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Optional

from cortex.extensions.llm._models import CascadeTier, IntentProfile

if TYPE_CHECKING:
    from cortex.extensions.llm._models import BaseProvider

logger = logging.getLogger("cortex.extensions.llm.cascade")


def classify_tier(provider: BaseProvider, intent: IntentProfile) -> CascadeTier:
    """Classify which cascade tier a fallback belongs to.

    - typed-match:  provider declares the prompt's intent in its affinity
    - safety-net:   provider is GENERAL-only or from a different domain
    """
    if intent in provider.intent_affinity:
        return CascadeTier.TYPED_MATCH
    return CascadeTier.SAFETY_NET


class CascadeManager:
    """Manages the lifecycle and ordering of providers within a cascade."""

    def __init__(
        self,
        negative_ttl: float = 300.0,
        positive_ttl: float = 600.0,
    ) -> None:
        self.negative_ttl = negative_ttl
        self.positive_ttl = positive_ttl
        # provider_name -> (last_success_timestamp, latency_ms)
        self._a_records: dict[str, tuple[float, float]] = {}
        # provider_name -> nxdomain_timestamp (circuit broken)
        self._nxdomain_cache: dict[str, float] = {}

    def get_a_record(self, provider_name: str) -> Optional[tuple[float, float]]:
        """Return A-record (time, latency) if exists and fresh."""
        record = self._a_records.get(provider_name)
        if record and (time.time() - record[0]) < self.positive_ttl:
            return record
        return None

    def set_a_record(self, provider_name: str, latency_ms: float) -> None:
        """Cache successful A-record."""
        self._a_records[provider_name] = (time.time(), latency_ms)
        self._nxdomain_cache.pop(provider_name, None)

    def set_nx_record(self, provider_name: str) -> None:
        """Cache failed NX record (circuit broken)."""
        self._nxdomain_cache[provider_name] = time.time()
        self._a_records.pop(provider_name, None)

    def is_nxdomain_cached(self, provider_name: str) -> bool:
        """True if provider is in negative cache."""
        nx_at = self._nxdomain_cache.get(provider_name)
        if nx_at and (time.time() - nx_at) < self.negative_ttl:
            return True
        return False

    def promote_known_good(
        self,
        providers: list[BaseProvider],
        intent: IntentProfile,
    ) -> list[BaseProvider]:
        """Within a tier, promote A-record cached providers to the front.

        Known-good providers (fresh A-record) are sorted by latency
        (fastest first). Unknown providers maintain their original order.
        """
        known_good: list[tuple[BaseProvider, float]] = []
        unknown: list[BaseProvider] = []

        for p in providers:
            record = self.get_a_record(p.provider_name)
            if record:
                known_good.append((p, record[1]))
            else:
                unknown.append(p)

        # Sort known_good by latency (item[1])
        known_good.sort(key=lambda x: x[1])
        return [p for p, lat in known_good] + unknown
