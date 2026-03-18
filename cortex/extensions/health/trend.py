"""Trend detection — drift detection from health snapshots.

Ring buffer of last N scores. Computes slope to classify:
  - "improving" (positive slope)
  - "stable" (near-zero slope)
  - "degrading" (negative slope)

Supports optional SQLite persistence via health_history table.
"""

from __future__ import annotations

import logging
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("cortex.extensions.health.trend")


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

    # ─── SQLite Persistence ──────────────────────────────────

    @staticmethod
    def _ensure_table(conn: sqlite3.Connection) -> None:
        """Create health_history table if it doesn't exist."""
        conn.execute(
            "CREATE TABLE IF NOT EXISTS health_history ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  timestamp TEXT NOT NULL,"
            "  score REAL NOT NULL,"
            "  grade TEXT NOT NULL DEFAULT ''"
            ")"
        )

    def persist_to_db(self, db_path: str, score: float, grade: str = "") -> None:
        """Persist a health score snapshot to SQLite."""
        try:
            conn = sqlite3.connect(db_path, timeout=2.0)
            try:
                self._ensure_table(conn)
                conn.execute(
                    "INSERT INTO health_history (timestamp, score, grade) VALUES (?, ?, ?)",
                    (datetime.now(timezone.utc).isoformat(), score, grade),
                )
                conn.commit()
            finally:
                conn.close()
        except (sqlite3.Error, OSError) as e:
            logger.debug("Failed to persist health score: %s", e)

    def load_from_db(self, db_path: str, limit: int | None = None) -> None:
        """Seed ring buffer from historical DB records."""
        n = limit or self.window_size
        try:
            conn = sqlite3.connect(db_path, timeout=2.0)
            conn.row_factory = sqlite3.Row
            try:
                self._ensure_table(conn)
                cur = conn.execute(
                    "SELECT score FROM health_history ORDER BY id DESC LIMIT ?",
                    (n,),
                )
                rows = cur.fetchall()
                # Rows are newest-first; reverse for chronological push
                for row in reversed(rows):
                    self.push(row["score"])
            finally:
                conn.close()
        except (sqlite3.Error, OSError) as e:
            logger.debug("Failed to load health history: %s", e)

    @staticmethod
    def query_history(db_path: str, limit: int = 20) -> list[dict[str, object]]:
        """Query persisted health history for display."""
        try:
            conn = sqlite3.connect(db_path, timeout=2.0)
            conn.row_factory = sqlite3.Row
            try:
                TrendDetector._ensure_table(conn)
                cur = conn.execute(
                    "SELECT timestamp, score, grade FROM health_history ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]
            finally:
                conn.close()
        except (sqlite3.Error, OSError):
            return []

    def __repr__(self) -> str:
        return (
            f"TrendDetector(samples={self.sample_count}, "
            f"drift={self.detect_drift()}, "
            f"slope={self.slope():.2f})"
        )
