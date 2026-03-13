"""CortexEngine health mixin — engine.health_check() API.

Cached collector, TrendDetector, configurable thresholds.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.health.collector import HealthCollector
from cortex.health.models import (
    Grade,
    HealthReport,
    HealthScore,
    HealthThresholds,
)
from cortex.health.scorer import HealthScorer
from cortex.health.trend import TrendDetector

logger = logging.getLogger("cortex.health")


class HealthMixin:
    """Health mixin for CortexEngine.

    Provides:
      - ``health_check()`` → quick boolean dict
      - ``health_score()`` → HealthScore (sealed Grade)
      - ``health_report()`` → HealthReport with trend + recommendations
    """

    _db_path: Any
    _health_collector: HealthCollector | None = None
    _health_trend: TrendDetector | None = None
    _health_thresholds: HealthThresholds | None = None

    def _get_health_collector(self) -> HealthCollector:
        """Lazily create and cache the HealthCollector."""
        if self._health_collector is None:
            db_path = getattr(self, "_db_path", "")
            self._health_collector = HealthCollector(db_path=db_path)
        return self._health_collector

    def _get_trend_detector(self) -> TrendDetector:
        """Lazily create the TrendDetector."""
        if self._health_trend is None:
            self._health_trend = TrendDetector()
        return self._health_trend

    def _get_thresholds(self) -> HealthThresholds:
        """Lazily create thresholds config."""
        if self._health_thresholds is None:
            self._health_thresholds = HealthThresholds()
        return self._health_thresholds

    async def health_check(self, **kwargs: Any) -> dict[str, Any]:
        """Quick boolean health check."""
        hs = await self.health_score(**kwargs)
        return {
            "healthy": hs.healthy,
            "score": round(hs.score, 2),
            "grade": hs.grade.letter,
        }

    async def health_score(self, **kwargs: Any) -> HealthScore:
        """Compute the full health score, record trend."""
        collector = self._get_health_collector()
        metrics = collector.collect_all()
        weights = kwargs.get("weights")
        hs = HealthScorer.score(metrics, weights=weights)

        # Feed trend detector
        trend = self._get_trend_detector()
        trend.push(hs.score)

        return hs

    async def health_report(self, **kwargs: Any) -> HealthReport:
        """Full report with trend, recommendations, warnings."""
        hs = await self.health_score(**kwargs)
        t = self._get_thresholds()

        recommendations: list[str] = []
        warnings: list[str] = []

        for m in hs.metrics:
            if m.value < t.critical:
                warnings.append(f"{m.name}: CRITICAL ({m.value:.0%})")
            elif m.value < t.degraded:
                warnings.append(f"{m.name}: degraded ({m.value:.0%})")
            elif m.value < t.improve:
                recommendations.append(f"{m.name}: could improve ({m.value:.0%})")

        if hs.grade <= Grade.FAILED:
            warnings.append(
                f"Overall health is FAILED ({hs.grade.letter}) — immediate investigation required"
            )
        elif hs.grade <= Grade.DEGRADED:
            warnings.append(f"Overall health is DEGRADED ({hs.grade.letter})")
        elif hs.grade <= Grade.ACCEPTABLE:
            recommendations.append("Run `cortex compact` to reduce entropy")
        elif hs.grade <= Grade.GOOD:
            recommendations.append("Health is Good — consider ledger verification")

        trend = self._get_trend_detector()
        drift = trend.detect_drift()

        if drift == "degrading":
            warnings.append(f"Health trend is DEGRADING (slope={trend.slope():.2f})")

        db_path = str(getattr(self, "_db_path", ""))
        return HealthReport(
            score=hs,
            recommendations=recommendations,
            warnings=warnings,
            trend=drift,
            db_path=db_path,
        )
