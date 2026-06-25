# [C5-REAL] Exergy-Maximized
"""Shannon Entropy-modulated metrics for Evolution Engine.

Implements recursive TTL adaptation via logistic sigmoid decay
based on the volatility (entropy) of the afferent metric stream.
"""

import logging
from pathlib import Path

from legacy_research.extensions.evolution.agents import AgentDomain
from legacy_research.extensions.evolution.cortex_metrics import (
    _DEFAULT_DB,
    DomainMetrics,
)

logger = logging.getLogger("cortex.extensions.evolution.shannon")


class CortexMetrics:
    """Sync CORTEX DB querier with per-domain caching.

    Thread-safe. Uses raw sqlite3 to avoid async conflicts
    when called from asyncio.to_thread offloads.
    """

    _BASE_TTL: float = 60.0
    _MAX_HISTORY: int = 20

    def __init__(self, db_path: str | Path = _DEFAULT_DB) -> None:
        self._db_path = Path(db_path)
        self._cache: dict[AgentDomain, DomainMetrics] = {}
        self._cache_time: float = 0.0
        self._cache_ttl: float = self._BASE_TTL
        self._history: list[dict[AgentDomain, DomainMetrics]] = []

    _ENTROPY_K: float = 1.5
    _ENTROPY_THETA: float = 2.0
    _TTL_FLOOR: float = 5.0
    _TTL_CEIL: float = 120.0

    def get_all_metrics(self) -> dict[AgentDomain, DomainMetrics]:
        """Get metrics for all 10 domains (cached)."""
        if self._is_cache_valid():  # pyright: ignore[reportAttributeAccessIssue]
            return dict(self._cache)
        self._refresh()  # pyright: ignore[reportAttributeAccessIssue]
        return dict(self._cache)

    def get_domain(self, domain: AgentDomain) -> DomainMetrics:
        """Get cached metrics for a single domain."""
        if self._is_cache_valid() and domain in self._cache:  # pyright: ignore[reportAttributeAccessIssue]
            return self._cache[domain]
        self._refresh()  # pyright: ignore[reportAttributeAccessIssue]
        return self._cache.get(domain, DomainMetrics(domain=domain))

    def get_domain_metrics(self, domain: AgentDomain) -> DomainMetrics:
        """Alias for strategies.py compatibility."""
        return self.get_domain(domain)
