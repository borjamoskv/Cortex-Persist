"""MEJORAlo Effectiveness Tracker — quantifies whether CORTEX is actually improving code.

Answers the question: "Is this project getting better over time, or are we just churning?"
Uses historical session data from the mejoralo ledger to compute trends,
decay risk, and stagnation alerts.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any, Optional

from cortex.engine import CortexEngine
from cortex.extensions.mejoralo.ledger import get_history

__all__ = ["EffectivenessTracker", "TrendReport"]

logger = logging.getLogger("cortex.extensions.mejoralo.effectiveness")

_MIN_SESSIONS_FOR_TREND = 3
_STAGNATION_WINDOW = 5


@dataclass
class TrendReport:
    """Summary of code quality trajectory for a project."""

    project: str
    sessions_analyzed: int
    latest_score: Optional[int]
    avg_delta: float
    positive_rate: float  # % of heals that actually improved score
    score_trend: str  # "improving", "stable", "declining", "insufficient_data"
    decay_risk: float  # 0.0 = no risk, 1.0 = critical
    stagnant: bool  # True if last N heals had delta <= 0
    scores: list[int] = field(default_factory=list)
    deltas: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "sessions_analyzed": self.sessions_analyzed,
            "latest_score": self.latest_score,
            "avg_delta": round(self.avg_delta, 2),
            "positive_rate": round(self.positive_rate, 2),
            "score_trend": self.score_trend,
            "decay_risk": round(self.decay_risk, 3),
            "stagnant": self.stagnant,
        }

    @property
    def summary(self) -> str:
        """Human-readable one-liner."""
        icon = {"improving": "📈", "stable": "➡️", "declining": "📉"}.get(self.score_trend, "❓")
        return (
            f"{icon} {self.project}: {self.score_trend} "
            f"(avg Δ{self.avg_delta:+.1f}, "
            f"{self.positive_rate:.0%} positive, "
            f"decay={self.decay_risk:.1%})"
        )


class EffectivenessTracker:
    """Analyzes mejoralo session history to measure real effectiveness."""

    def __init__(self, engine: CortexEngine):
        self.engine = engine

    def project_trend(self, project: str, window: int = 30) -> TrendReport:
        """Compute effectiveness trend for a project.

        Args:
            project: Project name to analyze.
            window: Maximum number of sessions to consider.

        Returns:
            TrendReport with trend analysis.
        """
        sessions = get_history(self.engine, project, limit=window)

        if len(sessions) < _MIN_SESSIONS_FOR_TREND:
            return TrendReport(
                project=project,
                sessions_analyzed=len(sessions),
                latest_score=sessions[0]["score_after"] if sessions else None,
                avg_delta=0.0,
                positive_rate=0.0,
                score_trend="insufficient_data",
                decay_risk=0.0,
                stagnant=False,
            )

        # Sessions come newest-first from ledger; reverse for chronological
        sessions_chrono = list(reversed(sessions))

        deltas = [s["delta"] for s in sessions_chrono if s["delta"] is not None]
        scores = [s["score_after"] for s in sessions_chrono if s["score_after"] is not None]

        avg_delta = statistics.mean(deltas) if deltas else 0.0
        positive_count = sum(1 for d in deltas if d > 0)
        positive_rate = positive_count / len(deltas) if deltas else 0.0

        latest_score = scores[-1] if scores else None
        stagnant = self.stagnation_alert(project, sessions=sessions)

        # Trend classification
        score_trend = self._classify_trend(deltas)

        # Decay risk
        decay = self.decay_risk(project, sessions=sessions)

        return TrendReport(
            project=project,
            sessions_analyzed=len(sessions),
            latest_score=latest_score,
            avg_delta=avg_delta,
            positive_rate=positive_rate,
            score_trend=score_trend,
            decay_risk=decay,
            stagnant=stagnant,
            scores=scores,
            deltas=deltas,
        )

    def decay_risk(
        self,
        project: str,
        sessions: Optional[list[dict[str, Any]]] = None,
    ) -> float:
        """Probability of score degradation (0.0 to 1.0).

        Based on:
        - Recent negative deltas (weight: 40%)
        - Decreasing score trajectory (weight: 30%)
        - Low positive rate (weight: 30%)
        """
        if sessions is None:
            sessions = get_history(self.engine, project, limit=20)

        if len(sessions) < _MIN_SESSIONS_FOR_TREND:
            return 0.0

        deltas = [s["delta"] for s in sessions if s["delta"] is not None]
        scores = [s["score_after"] for s in sessions if s["score_after"] is not None]

        if not deltas:
            return 0.0

        # Factor 1: Recent negative delta ratio (last 5 sessions)
        recent = deltas[-_STAGNATION_WINDOW:]
        negative_ratio = sum(1 for d in recent if d <= 0) / len(recent)

        # Factor 2: Score trajectory (linear regression slope approximation)
        if len(scores) >= 3:
            # Simple: compare mean of first half vs second half
            mid = len(scores) // 2
            first_half_mean = statistics.mean(scores[:mid]) if mid > 0 else 0
            second_half_mean = statistics.mean(scores[mid:])
            trajectory_decay = max(
                0.0,
                (first_half_mean - second_half_mean) / max(first_half_mean, 1),
            )
        else:
            trajectory_decay = 0.0

        # Factor 3: Low positive rate
        positive_rate = sum(1 for d in deltas if d > 0) / len(deltas)
        low_positive_penalty = max(0.0, 1.0 - positive_rate * 2)

        risk = 0.4 * negative_ratio + 0.3 * min(trajectory_decay, 1.0) + 0.3 * low_positive_penalty
        return min(risk, 1.0)

    def stagnation_alert(
        self,
        project: str,
        sessions: Optional[list[dict[str, Any]]] = None,
    ) -> bool:
        """True if last N heals had delta <= 0 (consecutive stagnation)."""
        if sessions is None:
            sessions = get_history(self.engine, project, limit=_STAGNATION_WINDOW)

        if len(sessions) < _STAGNATION_WINDOW:
            return False

        # Sessions come newest-first; check the most recent N
        recent = sessions[:_STAGNATION_WINDOW]
        return all((s.get("delta") or 0) <= 0 for s in recent)

    def _classify_trend(self, deltas: list[int]) -> str:
        """Classify the score trend as improving/stable/declining."""
        if not deltas or len(deltas) < _MIN_SESSIONS_FOR_TREND:
            return "insufficient_data"

        avg_delta = statistics.mean(deltas)
        recent_deltas = deltas[-_STAGNATION_WINDOW:]
        recent_avg = statistics.mean(recent_deltas) if recent_deltas else 0

        # Use recent trend as primary signal, overall as secondary
        if recent_avg > 1.0:
            return "improving"
        if recent_avg < -1.0:
            return "declining"

        # Check overall if recent is ambiguous
        if avg_delta > 0.5:
            return "improving"
        if avg_delta < -0.5:
            return "declining"

        return "stable"
