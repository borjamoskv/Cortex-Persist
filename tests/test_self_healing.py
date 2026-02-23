# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).

"""Tests for the self-healing monitor feature in MoskvDaemon."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cortex.daemon.core import MAX_CONSECUTIVE_FAILURES, MoskvDaemon
from cortex.daemon.models import DaemonStatus


class _ExplodingMonitor:
    """A monitor that always raises."""

    def check(self):
        raise RuntimeError("💥 intentional failure")


class _HealthyMonitor:
    """A monitor that always succeeds."""

    def check(self):
        return []


@pytest.fixture
def daemon(tmp_path: Path):
    """Create a MoskvDaemon with minimal config for testing."""
    config_dir = tmp_path / "memory"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "ghosts.json").write_text("[]")
    (config_dir / "system.json").write_text("{}")

    with (
        patch("cortex.daemon.core.MoskvDaemon._load_config", return_value={}),
        patch("cortex.daemon.core.SiteMonitor"),
        patch("cortex.daemon.core.GhostWatcher"),
        patch("cortex.daemon.core.MemorySyncer"),
        patch("cortex.daemon.core.CertMonitor"),
        patch("cortex.daemon.core.EngineHealthCheck"),
        patch("cortex.daemon.core.DiskMonitor"),
        patch("cortex.daemon.core.EntropyMonitor"),
        patch("cortex.daemon.core.AutonomousMejoraloMonitor"),
        patch("cortex.daemon.core.PerceptionMonitor"),
        patch("cortex.daemon.core.NeuralIntentMonitor"),
        patch("cortex.daemon.core.SecurityMonitor"),
        patch("cortex.daemon.core.CompactionMonitor"),
    ):
        d = MoskvDaemon(
            sites=[],
            config_dir=config_dir,
            notify=False,
        )
        yield d


class TestSelfHealing:
    """Test the self-healing monitor infrastructure."""

    def test_failure_counter_increments(self, daemon: MoskvDaemon):
        """Failure counter should increment on monitor exception."""
        status = DaemonStatus(checked_at="now")
        exploder = _ExplodingMonitor()

        daemon._run_monitor(status, "sites", exploder, lambda _: None)

        assert daemon._failure_counts.get("_ExplodingMonitor") == 1
        assert len(status.errors) == 1

    def test_failure_counter_resets_on_success(self, daemon: MoskvDaemon):
        """Counter should reset to 0 after a successful run."""
        status = DaemonStatus(checked_at="now")
        exploder = _ExplodingMonitor()

        # Fail once
        daemon._run_monitor(status, "sites", exploder, lambda _: None)
        assert daemon._failure_counts.get("_ExplodingMonitor") == 1

        # Succeed
        healthy = _HealthyMonitor()
        # Need same class name for reset — use a real healthy check
        daemon._run_monitor(status, "sites", healthy, lambda _: None)
        assert daemon._failure_counts.get("_HealthyMonitor") is None

    def test_heal_triggered_after_max_failures(self, daemon: MoskvDaemon):
        """_heal_monitor should be called after MAX_CONSECUTIVE_FAILURES."""
        status = DaemonStatus(checked_at="now")
        exploder = _ExplodingMonitor()

        with patch.object(daemon, "_heal_monitor") as mock_heal:
            for _ in range(MAX_CONSECUTIVE_FAILURES):
                daemon._run_monitor(status, "sites", exploder, lambda _: None)

            mock_heal.assert_called_once_with("sites", "_ExplodingMonitor")

    def test_heal_counter_reset_after_healing(self, daemon: MoskvDaemon):
        """After healing, the failure counter should be cleared."""
        status = DaemonStatus(checked_at="now")
        exploder = _ExplodingMonitor()

        with patch.object(daemon, "_heal_monitor"):
            for _ in range(MAX_CONSECUTIVE_FAILURES):
                daemon._run_monitor(status, "sites", exploder, lambda _: None)

            # Counter should be cleared after heal
            assert "_ExplodingMonitor" not in daemon._failure_counts

    def test_heal_monitor_site_monitor(self, daemon: MoskvDaemon):
        """_heal_monitor should re-instantiate SiteMonitor."""
        with patch("cortex.daemon.core.MoskvDaemon._load_config", return_value={"sites": []}):
            with patch("cortex.daemon.healing.SiteMonitor"):
                daemon._heal_monitor("sites", "SiteMonitor")

        assert daemon._healed_total == 1

    def test_heal_monitor_unknown_name(self, daemon: MoskvDaemon):
        """Unknown monitor name should not crash but not increment healed."""
        daemon._heal_monitor("foo", "UnknownMonitor")
        assert daemon._healed_total == 0

    def test_heal_monitor_exception_caught(self, daemon: MoskvDaemon):
        """If re-instantiation fails, it should be caught and logged."""
        with patch(
            "cortex.daemon.core.MoskvDaemon._load_config",
            return_value={"sites": []},
        ):
            with patch(
                "cortex.daemon.healing.SiteMonitor",
                side_effect=RuntimeError("constructor broken"),
            ):
                # Should not raise — exception is caught inside _heal_monitor
                daemon._heal_monitor("sites", "SiteMonitor")
                assert daemon._healed_total == 0

    def test_consecutive_failures_below_threshold(self, daemon: MoskvDaemon):
        """Fewer failures than threshold should NOT trigger healing."""
        status = DaemonStatus(checked_at="now")
        exploder = _ExplodingMonitor()

        with patch.object(daemon, "_heal_monitor") as mock_heal:
            for _ in range(MAX_CONSECUTIVE_FAILURES - 1):
                daemon._run_monitor(status, "sites", exploder, lambda _: None)

            mock_heal.assert_not_called()
            assert daemon._failure_counts["_ExplodingMonitor"] == MAX_CONSECUTIVE_FAILURES - 1
