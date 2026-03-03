"""Tests for Moltbook Analytics — pure logic, no HTTP (Ω₂ Entropic Asymmetry)."""

import pytest

from moltbook.analytics import AnalyticsStore, KarmaSnapshot, PostMetrics


class TestPostMetrics:
    """Score and engagement rate calculations."""

    def test_score(self):
        pm = PostMetrics(post_id="p1", upvotes=25, downvotes=3)
        assert pm.score == 22

    def test_engagement_rate(self):
        pm = PostMetrics(post_id="p2", upvotes=10, downvotes=2, comment_count=6)
        # engagement_rate = comments / total_votes = 6 / 12 = 0.5
        assert pm.engagement_rate == pytest.approx(0.5)

    def test_engagement_rate_zero_votes(self):
        pm = PostMetrics(post_id="p3", upvotes=0, downvotes=0, comment_count=5)
        assert pm.engagement_rate == 0.0


class TestAnalyticsStore:
    """Persistence roundtrip — save and load."""

    def test_save_and_load(self, tmp_path):
        store = AnalyticsStore(
            post_metrics=[
                PostMetrics(post_id="x1", title="Alpha", upvotes=10, downvotes=1),
                PostMetrics(post_id="x2", title="Beta", upvotes=5, downvotes=0, comment_count=3),
            ],
            karma_history=[
                KarmaSnapshot(karma=42),
                KarmaSnapshot(karma=55),
            ],
        )
        path = tmp_path / "analytics.json"
        store.save(path)

        loaded = AnalyticsStore.load(path)
        assert len(loaded.post_metrics) == 2
        assert len(loaded.karma_history) == 2
        assert loaded.post_metrics[0].post_id == "x1"
        assert loaded.post_metrics[0].title == "Alpha"
        assert loaded.post_metrics[1].score == 5
        assert loaded.karma_history[-1].karma == 55
