# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX LLM Router — Anycast-Style Weighted Provider Pool.

ProviderMetrics: EWMA latency + success rate per provider.
WeightedProviderPool: DNS Anycast routing — fastest provider wins.

Extraído de router.py (Ω₂ Landauer split).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from cortex.extensions.llm._models import BaseProvider

__all__ = ["ProviderMetrics", "WeightedProviderPool"]

logger = logging.getLogger("cortex.extensions.llm.pool")


@dataclass()
class ProviderMetrics:
    """EWMA-based latency and success tracking per provider.

    DNS Anycast routes to the nearest (fastest) server. CORTEX does the
    same at the semantic level: providers that respond faster accumulate
    higher weight and get more traffic.

    Uses Exponentially Weighted Moving Average (EWMA) for latency with
    α=0.3 (recent observations bias). Success rate is a simple ratio.

    Axiom: Ω₅ (Antifragile) — metrics feed the system, not just report.
    """

    total_calls: int = 0
    total_successes: int = 0
    total_failures: int = 0
    ewma_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    last_latency_ms: float = 0.0

    _EWMA_ALPHA: float = field(default=0.3, repr=False)

    def record_success(self, latency_ms: float) -> None:
        """Record a successful call with its latency."""
        self.total_calls += 1
        self.total_successes += 1
        self._update_latency(latency_ms)

    def record_failure(self, latency_ms: float) -> None:
        """Record a failed call with its latency."""
        self.total_calls += 1
        self.total_failures += 1
        self._update_latency(latency_ms)

    def _update_latency(self, latency_ms: float) -> None:
        """Update EWMA and extrema."""
        self.last_latency_ms = latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)

        if self.total_calls == 1:
            self.ewma_latency_ms = latency_ms
        else:
            alpha = self._EWMA_ALPHA
            self.ewma_latency_ms = alpha * latency_ms + (1 - alpha) * self.ewma_latency_ms

    @property
    def success_rate(self) -> float:
        """Success ratio [0.0, 1.0]. Returns 1.0 if no calls yet."""
        if self.total_calls == 0:
            return 1.0
        return self.total_successes / self.total_calls

    @property
    def weight(self) -> float:
        """Routing weight: inversely proportional to EWMA latency.

        Faster providers get higher weight. Failed providers get penalized
        by the success_rate multiplier (0.0 = always fails → weight 0).

        Weight = success_rate / max(ewma_latency_ms, 1.0)

        This produces a natural ranking where a provider at 100ms with
        100% success has 10x the weight of one at 1000ms with 100% success.
        """
        if self.total_calls == 0:
            return 1.0  # equal chance until observed
        return self.success_rate / max(self.ewma_latency_ms, 1.0)


class WeightedProviderPool:
    """DNS Anycast-style weighted provider pool.

    Same interface (BaseProvider), multiple backends. Routing by observed
    latency and success rate, using EWMA. Faster providers accumulate
    higher weight and get selected more often.

    Axiom: Ω₂ (entropic cost → route to lowest-cost provider) +
           Ω₅ (metrics anti-fragility → self-optimizing).
    """

    def __init__(self) -> None:
        self._metrics: dict[str, ProviderMetrics] = {}

    def get_or_create(self, provider_name: str) -> ProviderMetrics:
        """Get metrics for a provider, creating if new."""
        if provider_name not in self._metrics:
            self._metrics[provider_name] = ProviderMetrics()
        return self._metrics[provider_name]

    def record_success(self, provider_name: str, latency_ms: float) -> None:
        """Record a successful provider call."""
        self.get_or_create(provider_name).record_success(latency_ms)

    def record_failure(self, provider_name: str, latency_ms: float) -> None:
        """Record a failed provider call."""
        self.get_or_create(provider_name).record_failure(latency_ms)

    def get_success_rate(self, provider_name: str) -> float:
        """Get success rate [0.0, 1.0] for adaptive behavior."""
        if provider_name not in self._metrics:
            return 1.0  # Benefit of the doubt for new providers
        return self._metrics[provider_name].success_rate

    def select_weighted(self, providers: list[BaseProvider]) -> BaseProvider:
        """Select a provider weighted by inverse EWMA latency.

        Providers with no history get weight 1.0 (benefit of the doubt).
        Selection is deterministic: always picks the highest-weight provider.
        For probabilistic selection, use select_weighted_random().
        """
        if not providers:
            raise ValueError("No providers to select from")
        if len(providers) == 1:
            return providers[0]

        best = providers[0]
        best_weight = self.get_or_create(best.provider_name).weight
        for p in providers[1:]:
            w = self.get_or_create(p.provider_name).weight
            if w > best_weight:
                best = p
                best_weight = w

        logger.debug(
            "Anycast selected: %s (weight=%.6f)",
            best.provider_name,
            best_weight,
        )
        return best

    def rank(self, providers: list[BaseProvider]) -> list[BaseProvider]:
        """Sort providers by weight (highest first).

        Enables weight-aware cascade ordering: the router tries the
        historically fastest provider first, falling back down the ranking.
        """
        return sorted(
            providers,
            key=lambda p: self.get_or_create(p.provider_name).weight,
            reverse=True,
        )

    def snapshot(self) -> dict[str, dict[str, float]]:
        """Observability: current metrics for all tracked providers."""
        return {
            name: {
                "ewma_latency_ms": round(m.ewma_latency_ms, 2),
                "success_rate": round(m.success_rate, 4),
                "weight": round(m.weight, 6),
                "total_calls": m.total_calls,
            }
            for name, m in self._metrics.items()
        }

    def clear(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
