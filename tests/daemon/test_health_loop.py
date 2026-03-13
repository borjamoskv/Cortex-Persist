"""Tests for cortex.daemon.health_loop — autonomous health monitoring."""

from __future__ import annotations

from cortex.daemon.health_loop import HealthLoop


class TestHealthLoop:
    """Tests for HealthLoop tick and alerting logic."""

    def test_tick_returns_data(self):
        """Tick should return a health data dict."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        data = loop.tick()
        assert data is not None
        assert "score" in data
        assert "grade" in data
        assert "healthy" in data
        assert isinstance(data["score"], float)

    def test_tick_grade_stored(self):
        """After tick, last_grade should be updated."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        loop.tick()
        assert loop._last_grade != ""

    def test_healthy_boolean(self):
        """Healthy should be True when score >= 40."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        data = loop.tick()
        assert data is not None
        if data["score"] >= 40.0:
            assert data["healthy"] is True
        else:
            assert data["healthy"] is False

    def test_grade_change_detection(self):
        """Grade change should be detected between ticks."""
        notifications: list[str] = []

        def fake_notify(title, body):
            notifications.append(title)

        loop = HealthLoop(
            db_path="/tmp/nonexistent.db",
            notify_fn=fake_notify,
        )

        # First tick sets baseline
        loop.tick()
        # Simulate grade drop
        loop._last_grade = "S"
        loop.tick()

        # If current grade < S, should have triggered notification
        if loop._last_grade != "S":
            assert len(notifications) > 0

    def test_persist_snapshot_noop_without_engine(self):
        """persist_snapshot should be no-op when engine lacks store_sync."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        data = loop.tick()
        assert data is not None

        # Should not crash with a mock engine
        class MockEngine:
            def store_sync(self, *args, **kwargs):
                pass

        loop.persist_snapshot(MockEngine(), data)

    def test_interval_default(self):
        """Default interval should be 300 seconds."""
        loop = HealthLoop()
        assert loop._interval == 300

    def test_custom_interval(self):
        """Custom interval should be respected."""
        loop = HealthLoop(interval=60)
        assert loop._interval == 60

    def test_metrics_in_tick(self):
        """Tick results should include metrics list."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        data = loop.tick()
        assert data is not None
        assert "metrics" in data
        assert isinstance(data["metrics"], list)
        for m in data["metrics"]:
            assert "name" in m
            assert "value" in m

    def test_multiple_ticks_stable(self):
        """Multiple ticks should be stable (no crash)."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        for _ in range(5):
            data = loop.tick()
            assert data is not None
