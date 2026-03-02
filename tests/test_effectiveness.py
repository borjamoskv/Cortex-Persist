"""Tests for MEJORAlo EffectivenessTracker.

Uses mock session data to validate trend analysis,
decay risk scoring, and stagnation detection.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cortex.mejoralo.effectiveness import (
    EffectivenessTracker,
    TrendReport,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _make_sessions(
    scores: list[tuple[int, int]],
) -> list[dict]:
    """Create mock session dicts from (before, after) tuples.

    Returns newest-first (as get_history does).
    """
    sessions = []
    for i, (before, after) in enumerate(scores):
        sessions.append(
            {
                "id": i + 1,
                "content": f"Session {i + 1}",
                "created_at": f"2026-03-0{min(i + 1, 9)}T12:00:00Z",
                "score_before": before,
                "score_after": after,
                "delta": after - before,
                "actions": ["autonomous_heal"],
            }
        )
    # Return newest-first (reverse chronological)
    return list(reversed(sessions))


def _tracker_with_sessions(sessions: list[dict]) -> EffectivenessTracker:
    """Create a tracker with mocked get_history."""
    engine = MagicMock()
    tracker = EffectivenessTracker(engine)
    return tracker, sessions


# ── Tests ────────────────────────────────────────────────────────────


class TestProjectTrend:
    """Test project_trend() analysis."""

    def test_insufficient_data(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions([(60, 65)])  # Only 1 session

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            trend = tracker.project_trend("test")

        assert trend.score_trend == "insufficient_data"
        assert trend.sessions_analyzed == 1

    def test_improving_trend(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions(
            [
                (50, 55),
                (55, 60),
                (60, 68),
                (68, 75),
                (75, 82),
            ]
        )

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            trend = tracker.project_trend("test")

        assert trend.score_trend == "improving"
        assert trend.avg_delta > 0
        assert trend.positive_rate == 1.0
        assert trend.latest_score == 82

    def test_declining_trend(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions(
            [
                (80, 78),
                (78, 75),
                (75, 72),
                (72, 68),
                (68, 65),
            ]
        )

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            trend = tracker.project_trend("test")

        assert trend.score_trend == "declining"
        assert trend.avg_delta < 0
        assert trend.positive_rate == 0.0

    def test_stable_trend(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions(
            [
                (70, 71),
                (71, 70),
                (70, 71),
                (71, 70),
                (70, 70),
            ]
        )

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            trend = tracker.project_trend("test")

        assert trend.score_trend == "stable"

    def test_trend_report_to_dict(self):
        report = TrendReport(
            project="test",
            sessions_analyzed=10,
            latest_score=75,
            avg_delta=2.5,
            positive_rate=0.8,
            score_trend="improving",
            decay_risk=0.15,
            stagnant=False,
        )
        d = report.to_dict()
        assert d["project"] == "test"
        assert d["avg_delta"] == 2.5
        assert d["stagnant"] is False

    def test_trend_report_summary(self):
        report = TrendReport(
            project="cortex",
            sessions_analyzed=5,
            latest_score=80,
            avg_delta=3.0,
            positive_rate=0.8,
            score_trend="improving",
            decay_risk=0.1,
            stagnant=False,
        )
        assert "📈" in report.summary
        assert "cortex" in report.summary


class TestDecayRisk:
    """Test decay_risk() calculation."""

    def test_zero_risk_with_all_positive(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions(
            [
                (50, 55),
                (55, 60),
                (60, 65),
                (65, 70),
                (70, 75),
            ]
        )

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            risk = tracker.decay_risk("test")

        assert risk < 0.2  # Very low risk

    def test_high_risk_with_declining(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions(
            [
                (80, 75),
                (75, 70),
                (70, 65),
                (65, 60),
                (60, 55),
            ]
        )

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            risk = tracker.decay_risk("test")

        assert risk > 0.5  # High risk

    def test_insufficient_data_returns_zero(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions([(60, 65)])

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            risk = tracker.decay_risk("test")

        assert risk == 0.0


class TestStagnationAlert:
    """Test stagnation_alert() detection."""

    def test_not_stagnant_with_improvements(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions(
            [
                (50, 55),
                (55, 60),
                (60, 65),
                (65, 70),
                (70, 75),
            ]
        )

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            assert tracker.stagnation_alert("test") is False

    def test_stagnant_with_all_zero_deltas(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions(
            [
                (60, 60),
                (60, 60),
                (60, 60),
                (60, 60),
                (60, 60),
            ]
        )

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            assert tracker.stagnation_alert("test") is True

    def test_stagnant_with_negative_deltas(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions(
            [
                (60, 58),
                (58, 57),
                (57, 55),
                (55, 54),
                (54, 53),
            ]
        )

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            assert tracker.stagnation_alert("test") is True

    def test_not_stagnant_with_insufficient_data(self):
        engine = MagicMock()
        tracker = EffectivenessTracker(engine)
        sessions = _make_sessions([(60, 60), (60, 60)])

        with patch("cortex.mejoralo.effectiveness.get_history", return_value=sessions):
            assert tracker.stagnation_alert("test") is False
