"""Policy Mixin for Forgetting Oracle.

Adjusts the cache eviction parameters dynamically in response to regret rates.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.engine.forgetting_models import EvictionVerdict, OracleReport, PolicyRecommendation

logger = logging.getLogger("cortex.oracle.policy")


class PolicyMixin:
    """Auto-adjusts cache eviction parameters based on evaluation results."""

    _cache: Any

    def _calc_regret_rate(self, verdicts: list[EvictionVerdict]) -> float:
        """Fraction of verdicts that were regrettable."""
        if not verdicts:
            return 0.0
        return sum(1 for v in verdicts if v.was_regrettable) / len(verdicts)

    def _derive_recommendation(
        self,
        verdicts: list[EvictionVerdict],
        regret_rate: float,
    ) -> PolicyRecommendation:
        """Derive policy recommendation from verdicts."""
        if regret_rate <= 0.05:
            return PolicyRecommendation.OPTIMAL

        regretted = [v for v in verdicts if v.was_regrettable]
        causal_errors = [v for v in regretted if v.causal_weight > 0.7]
        root_errors = [v for v in regretted if v.causal_depth > 0]
        ttl_errors = [v for v in regretted if v.reason == "ttl_expired"]
        lru_errors = [v for v in regretted if v.reason == "lru_capacity"]

        # Strongest signal: evicting causal chain roots
        if root_errors and len(root_errors) > len(regretted) / 2:
            return PolicyRecommendation.PROTECT_CAUSAL_ROOTS
        if causal_errors and len(causal_errors) > len(lru_errors):
            return PolicyRecommendation.PRIORITIZE_CAUSAL
        if len(ttl_errors) > len(lru_errors):
            return PolicyRecommendation.INCREASE_TTL
        return PolicyRecommendation.REDUCE_CAPACITY

    def _calc_policy_deltas(
        self,
        regret_rate: float,
        verdicts: list[EvictionVerdict],
    ) -> tuple[float, int]:
        """Calculate TTL and capacity adjustment deltas proportional to error rate."""
        if regret_rate <= 0.05:
            return 0.0, 0

        # TTL: aumentar proporcionalmente al regret rate (máx +1800s)
        ttl_delta = min(1800.0, regret_rate * 3600.0)

        # Capacidad: aumentar un 15% si hay errores LRU
        lru_error_rate = sum(
            1 for v in verdicts if v.was_regrettable and v.reason == "lru_capacity"
        ) / max(len(verdicts), 1)
        capacity_delta = int(50 * lru_error_rate) if lru_error_rate > 0.1 else 0

        return ttl_delta, capacity_delta

    def _apply_policy_adjustment(self, report: OracleReport) -> None:
        """Auto-adjust active cache parameters when regret_rate exceeds threshold."""
        if not self._cache:
            return

        if report.suggested_ttl_delta > 0:
            old_ttl = self._cache.ttl
            self._cache.ttl = int(old_ttl + report.suggested_ttl_delta)
            logger.warning(
                "🔧 [ORACLE] Auto-adjusted TTL: %ds → %ds (+%.0fs)",
                old_ttl,
                self._cache.ttl,
                report.suggested_ttl_delta,
            )

        if report.suggested_capacity_delta > 0:
            old_cap = self._cache.capacity
            self._cache.capacity = old_cap + report.suggested_capacity_delta
            logger.warning(
                "🔧 [ORACLE] Auto-adjusted Capacity: %d → %d (+%d)",
                old_cap,
                self._cache.capacity,
                report.suggested_capacity_delta,
            )
