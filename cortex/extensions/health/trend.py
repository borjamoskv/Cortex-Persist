"""Trend detection — drift detection from health snapshots.

Ring buffer of last N scores. Computes slope to classify:
  - "improving" (positive slope)
  - "stable" (near-zero slope)
  - "degrading" (negative slope)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class TrendDetector:
    """Detect health score trends over time.

    Maintains a ring buffer of scores. After at least 3 samples,
    computes a linear slope to classify drift direction.
    """

    window_size: int = 12  # 1 hour at 5-min intervals
    _scores: deque[float] = field(
        default_factory=lambda: deque(maxlen=12),
        repr=False,
    )

    def __post_init__(self) -> None:
        # Ensure maxlen matches window_size
        if self._scores.maxlen != self.window_size:
            object.__setattr__(
                self,
                "_scores",
                deque(self._scores, maxlen=self.window_size),
            )

    def push(self, score: float) -> None:
        """Record a new health score."""
        self._scores.append(score)

    def slope(self) -> float:
        """Compute linear regression slope.

        Returns 0.0 if fewer than 2 samples.
        Positive = improving, Negative = degrading.
        """
        n = len(self._scores)
        if n < 2:
            return 0.0

        # Simple OLS slope: Σ((x-x̄)(y-ȳ)) / Σ((x-x̄)²)
        x_mean = (n - 1) / 2.0
        y_mean = sum(self._scores) / n

        numerator = 0.0
        denominator = 0.0
        for i, y in enumerate(self._scores):
            dx = i - x_mean
            numerator += dx * (y - y_mean)
            denominator += dx * dx

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def detect_drift(self) -> str:
        """Classify the current trend.

        Returns:
            "improving", "stable", or "degrading"
        """
        s = self.slope()
        if s > 0.5:
            return "improving"
        elif s < -0.5:
            return "degrading"
        return "stable"

    @property
    def sample_count(self) -> int:
        """Number of samples in the buffer."""
        return len(self._scores)

    def __repr__(self) -> str:
        return (
            f"TrendDetector(samples={self.sample_count}, "
            f"drift={self.detect_drift()}, "
            f"slope={self.slope():.2f})"
        )
