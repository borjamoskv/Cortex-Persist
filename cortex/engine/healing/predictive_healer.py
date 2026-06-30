# [C5-REAL] Exergy-Maximized
"""Predictive Healer - Proactive Failure Prevention for Level 5+6.

Analyzes telemetry trends to predict failures BEFORE they happen
and applies preventive repairs. Transforms L5 from reactive to proactive.

Detection methods:
    1. Linear regression on error rate (trending up?)
    2. Latency drift detection (p99 creeping toward timeout?)
    3. Seasonal pattern matching (recurring failures at intervals?)
    4. Cortisol momentum (endocrine stress accumulating?)

Reality Level: C5-REAL
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from cortex.engine.analytics.performance_tracker import PerformanceTracker
from cortex.engine.uncategorized.endocrine import ENDOCRINE, HormoneType

__all__ = [
    "Prediction",
    "PredictionType",
    "PredictiveHealer",
]

logger = logging.getLogger("cortex.engine.predictive")


# ─── Types ────────────────────────────────────────────────────────


class PredictionType:
    ERROR_RATE_RISING = "error_rate_rising"
    LATENCY_DRIFT = "latency_drift"
    TIMEOUT_APPROACHING = "timeout_approaching"
    RECURRING_PATTERN = "recurring_pattern"
    CORTISOL_MOMENTUM = "cortisol_momentum"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class Prediction:
    """A predicted future failure."""

    type: str
    subsystem: str
    confidence: float  # 0.0–1.0
    estimated_time_to_failure_s: float
    current_value: float
    threshold: float
    trend_slope: float
    recommended_action: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "subsystem": self.subsystem,
            "confidence": round(self.confidence, 3),
            "estimated_ttf_s": round(self.estimated_time_to_failure_s, 1),
            "current_value": round(self.current_value, 4),
            "threshold": round(self.threshold, 4),
            "trend_slope": round(self.trend_slope, 6),
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp,
        }

    @property
    def is_critical(self) -> bool:
        return self.confidence > 0.8 and self.estimated_time_to_failure_s < 60


# ─── Trend Analysis ──────────────────────────────────────────────


@dataclass
class _TrendWindow:
    """Sliding window of (timestamp, value) pairs for trend analysis."""

    max_size: int = 100
    _data: deque[tuple[float, float]] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        self._data = deque(maxlen=self.max_size)

    def push(self, value: float, timestamp: float | None = None) -> None:
        t = time.monotonic() if timestamp is None else timestamp
        self._data.append((t, value))

    @property
    def size(self) -> int:
        return len(self._data)

    def linear_regression(self) -> tuple[float, float, float]:
        """Returns (slope, intercept, r_squared).

        Slope > 0 = metric increasing over time.
        """
        n = len(self._data)
        if n < 3:
            return 0.0, 0.0, 0.0

        data = list(self._data)
        # Normalize timestamps to start at 0
        t0 = data[0][0]
        xs = [t - t0 for t, _ in data]
        ys = [v for _, v in data]

        mean_x = sum(xs) / n
        mean_y = sum(ys) / n

        ss_xx = sum((x - mean_x) ** 2 for x in xs)
        ss_yy = sum((y - mean_y) ** 2 for y in ys)
        ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))

        if ss_xx == 0:
            return 0.0, mean_y, 0.0

        slope = ss_xy / ss_xx
        intercept = mean_y - slope * mean_x

        r_squared = (ss_xy**2) / (ss_xx * ss_yy) if ss_yy > 0 else 0.0

        return slope, intercept, r_squared

    def extrapolate_to_threshold(self, threshold: float) -> float | None:
        """Estimate seconds until value reaches threshold.

        Returns None if trend is flat or moving away from threshold.
        """
        slope, intercept, r_sq = self.linear_regression()

        if slope == 0 or r_sq < 0.3:
            return None

        # Current value
        data = list(self._data)
        if not data:
            return None

        t0 = data[0][0]
        current_t = data[-1][0] - t0
        current_val = slope * current_t + intercept

        if slope > 0 and current_val < threshold:
            # Time to reach threshold
            target_t = (threshold - intercept) / slope
            remaining = target_t - current_t
            return max(0, remaining)
        if slope < 0 and current_val > threshold:
            target_t = (threshold - intercept) / slope
            remaining = target_t - current_t
            return max(0, remaining)

        return None

    @property
    def latest(self) -> float:
        if not self._data:
            return 0.0
        return self._data[-1][1]

    @property
    def mean(self) -> float:
        if not self._data:
            return 0.0
        return sum(v for _, v in self._data) / len(self._data)


# ─── Predictive Healer ───────────────────────────────────────────


class PredictiveHealer:
    """Proactive failure prediction engine.

    Analyzes telemetry trends and predicts failures before they happen.
    Generates preventive repair recommendations.

    Usage:
        healer = PredictiveHealer(tracker=perf_tracker)

        # Feed error rate samples
        healer.record_error_rate("api", 0.05)
        healer.record_error_rate("api", 0.08)
        healer.record_error_rate("api", 0.12)

        # Get predictions
        predictions = healer.predict_all()
        for p in predictions:
            if p.is_critical:
                logger.warning("%s: %s in %.0fs", p.subsystem, p.type, p.estimated_ttf_s)
    """

    def __init__(
        self,
        tracker: PerformanceTracker | None = None,
        error_rate_threshold: float = 0.2,
        latency_threshold_factor: float = 0.8,
        cortisol_threshold: float = 0.7,
        min_samples: int = 5,
    ) -> None:
        self._tracker = tracker
        self._error_rate_threshold = error_rate_threshold
        self._latency_threshold_factor = latency_threshold_factor
        self._cortisol_threshold = cortisol_threshold
        self._min_samples = min_samples

        # Trend windows per subsystem
        self._error_trends: dict[str, _TrendWindow] = {}
        self._latency_trends: dict[str, _TrendWindow] = {}
        self._cortisol_trend = _TrendWindow(max_size=200)

        # Error timestamps for pattern detection
        self._error_timestamps: dict[str, deque[float]] = {}

        # Prediction history
        self._predictions: deque[Prediction] = deque(maxlen=500)
        self._total_predictions = 0
        self._total_preventions = 0

    # ─── Data Ingestion ───────────────────────────────────────

    def record_error_rate(
        self, subsystem: str, rate: float, timestamp: float | None = None
    ) -> None:
        """Record an error rate sample for trend analysis."""
        if subsystem not in self._error_trends:
            self._error_trends[subsystem] = _TrendWindow(max_size=100)
        self._error_trends[subsystem].push(rate, timestamp)

    def record_latency(self, subsystem: str, p99_ms: float, timestamp: float | None = None) -> None:
        """Record a latency percentile for drift detection."""
        if subsystem not in self._latency_trends:
            self._latency_trends[subsystem] = _TrendWindow(max_size=100)
        self._latency_trends[subsystem].push(p99_ms, timestamp)

    def record_error_event(self, subsystem: str, timestamp: float | None = None) -> None:
        """Record an individual error event for pattern detection."""
        t = time.monotonic() if timestamp is None else timestamp
        if subsystem not in self._error_timestamps:
            self._error_timestamps[subsystem] = deque(maxlen=500)
        self._error_timestamps[subsystem].append(t)

    def record_cortisol(self, level: float, timestamp: float | None = None) -> None:
        """Record systemic cortisol level."""
        self._cortisol_trend.push(level, timestamp)

    def ingest_from_tracker(self) -> None:
        """Pull latest metrics from the PerformanceTracker."""
        if self._tracker is None:
            return

        now = time.monotonic()
        for name in self._tracker.subsystem_names:
            metrics = self._tracker.get_metrics(name)
            if metrics is None:
                continue
            self.record_error_rate(name, metrics.error_rate, now)
            self.record_latency(name, metrics.p99, now)

        cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)
        self.record_cortisol(cortisol, now)

    # ─── Prediction ───────────────────────────────────────────

    def predict_all(self) -> list[Prediction]:
        """Run all prediction models and return findings."""
        self.ingest_from_tracker()

        predictions: list[Prediction] = []

        # 1. Error rate trend
        for sub, trend in self._error_trends.items():
            pred = self._predict_error_rate(sub, trend)
            if pred:
                predictions.append(pred)

        # 2. Latency drift
        for sub, trend in self._latency_trends.items():
            pred = self._predict_latency_drift(sub, trend)
            if pred:
                predictions.append(pred)

        # 3. Recurring patterns
        for sub, timestamps in self._error_timestamps.items():
            pred = self._predict_recurring(sub, timestamps)
            if pred:
                predictions.append(pred)

        # 4. Cortisol momentum
        pred = self._predict_cortisol()
        if pred:
            predictions.append(pred)

        # Store
        for p in predictions:
            self._predictions.append(p)
            self._total_predictions += 1

        return predictions

    def _predict_error_rate(self, subsystem: str, trend: _TrendWindow) -> Prediction | None:
        """Predict if error rate is trending toward threshold."""
        if trend.size < self._min_samples:
            return None

        slope, intercept, r_sq = trend.linear_regression()

        # Only predict if slope is positive (error rate rising) and fit is decent
        if slope <= 0 or r_sq < 0.3:
            return None

        ttf = trend.extrapolate_to_threshold(self._error_rate_threshold)
        if ttf is None or ttf > 3600:  # Don't predict beyond 1 hour
            return None

        confidence = min(1.0, r_sq * (1.0 - (ttf / 3600)))

        return Prediction(
            type=PredictionType.ERROR_RATE_RISING,
            subsystem=subsystem,
            confidence=confidence,
            estimated_time_to_failure_s=ttf,
            current_value=trend.latest,
            threshold=self._error_rate_threshold,
            trend_slope=slope,
            recommended_action="PREEMPTIVE_BATCH_REDUCTION",
        )

    def _predict_latency_drift(self, subsystem: str, trend: _TrendWindow) -> Prediction | None:
        """Predict if latency is drifting toward timeout."""
        if trend.size < self._min_samples:
            return None

        slope, intercept, r_sq = trend.linear_regression()

        if slope <= 0 or r_sq < 0.3:
            return None

        # Get current timeout from optimizer or default
        timeout_ms = 5000.0
        if self._tracker:
            # Will be overridden by the stack's optimized value
            pass

        threshold = timeout_ms * self._latency_threshold_factor
        ttf = trend.extrapolate_to_threshold(threshold)

        if ttf is None or ttf > 1800:
            return None

        confidence = min(1.0, r_sq * 0.9)

        return Prediction(
            type=PredictionType.LATENCY_DRIFT,
            subsystem=subsystem,
            confidence=confidence,
            estimated_time_to_failure_s=ttf,
            current_value=trend.latest,
            threshold=threshold,
            trend_slope=slope,
            recommended_action="PREEMPTIVE_TIMEOUT_INCREASE",
        )

    def _predict_recurring(self, subsystem: str, timestamps: deque[float]) -> Prediction | None:
        """Detect recurring error patterns (periodic failures)."""
        if len(timestamps) < 4:
            return None

        ts = list(timestamps)
        intervals = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]

        if not intervals:
            return None

        mean_interval = sum(intervals) / len(intervals)
        if mean_interval == 0:
            return None

        variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
        cv = math.sqrt(variance) / mean_interval if mean_interval > 0 else float("inf")

        # Low coefficient of variation = regular pattern
        if cv < 0.3 and mean_interval < 300:  # Regular pattern under 5 min
            time_since_last = time.monotonic() - ts[-1]
            next_predicted = mean_interval - time_since_last

            if next_predicted > 0:
                confidence = max(0.0, min(1.0, 1.0 - cv))
                return Prediction(
                    type=PredictionType.RECURRING_PATTERN,
                    subsystem=subsystem,
                    confidence=confidence,
                    estimated_time_to_failure_s=next_predicted,
                    current_value=mean_interval,
                    threshold=0.0,
                    trend_slope=1.0 / mean_interval,
                    recommended_action="PREEMPTIVE_BREAKER_WARMUP",
                )

        return None

    def _predict_cortisol(self) -> Prediction | None:
        """Predict systemic stress overload from cortisol momentum."""
        if self._cortisol_trend.size < self._min_samples:
            return None

        slope, intercept, r_sq = self._cortisol_trend.linear_regression()

        if slope <= 0 or r_sq < 0.4:
            return None

        ttf = self._cortisol_trend.extrapolate_to_threshold(self._cortisol_threshold)
        if ttf is None or ttf > 600:  # 10 min horizon
            return None

        confidence = min(1.0, r_sq * 0.85)

        return Prediction(
            type=PredictionType.CORTISOL_MOMENTUM,
            subsystem="_system",
            confidence=confidence,
            estimated_time_to_failure_s=ttf,
            current_value=self._cortisol_trend.latest,
            threshold=self._cortisol_threshold,
            trend_slope=slope,
            recommended_action="PREEMPTIVE_CONSOLIDATION",
        )

    # ─── Prevention Tracking ──────────────────────────────────

    def record_prevention(self) -> None:
        """Record that a predicted failure was prevented."""
        self._total_preventions += 1

    # ─── Introspection ────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_predictions": self._total_predictions,
            "total_preventions": self._total_preventions,
            "prevention_rate": (self._total_preventions / max(1, self._total_predictions)),
            "tracked_subsystems": list(self._error_trends.keys()),
            "error_trend_samples": {k: v.size for k, v in self._error_trends.items()},
            "latency_trend_samples": {k: v.size for k, v in self._latency_trends.items()},
            "cortisol_samples": self._cortisol_trend.size,
        }

    def get_predictions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent predictions."""
        preds = list(self._predictions)
        return [p.to_dict() for p in preds[-limit:]]

    def get_critical_predictions(self) -> list[Prediction]:
        """Get only critical predictions (high confidence, imminent)."""
        return [p for p in self._predictions if p.is_critical]
