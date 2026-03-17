"""Tests for NightShift Crystal Daemon.

Verifies the lifecycle of the daemon, including the acquisition phase (Phase 1)
and the consolidation phase (Phase 2).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.extensions.swarm.nightshift_daemon import NightShiftCrystalDaemon


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.store = AsyncMock()
    return db


class TestNightShiftCrystalDaemon:
    @pytest.mark.asyncio
    @patch("cortex.extensions.swarm.nightshift_daemon.discover", new_callable=AsyncMock)
    @patch("cortex.extensions.swarm.nightshift_daemon.NightShiftPipeline.run", new_callable=AsyncMock)
    @patch("cortex.extensions.swarm.crystal_thermometer.scan_all_crystals", new_callable=AsyncMock)
    @patch("cortex.extensions.swarm.crystal_consolidator.consolidate", new_callable=AsyncMock)
    async def test_full_cycle_success(
        self, mock_consolidate, mock_scan, mock_run, mock_discover, mock_db
    ) -> None:
        """Test a complete cycle with successful acquisition and consolidation."""
        mock_discover.return_value = [{"type": "web", "url": "http://test.com"}]
        mock_run.return_value = {
            "crystals_count": 1,
            "crystals_forged": ["crystal-1"],
            "confidence": "C4",
            "is_paused": False,
        }
        mock_scan.return_value = [{"fact_id": "test", "quadrant": "ACTIVE"}]

        # mock_consolidate.return_value needs a to_dict method
        mock_consolidation_result = MagicMock()
        mock_consolidation_result.to_dict.return_value = {
            "purged": 0,
            "merged": 0,
            "promoted": 1,
            "total_scanned": 1,
        }
        mock_consolidate.return_value = mock_consolidation_result

        daemon = NightShiftCrystalDaemon(cortex_db=mock_db, max_crystals=2)
        report = await daemon.run_cycle()

        assert report["status"] == "complete"
        assert report["crystals"] == 1
        assert "consolidation" in report
        assert report["consolidation"]["promoted"] == 1

        mock_discover.assert_called_once()
        mock_run.assert_called_once()
        mock_scan.assert_called_once()
        mock_consolidate.assert_called_once()
        mock_db.store.assert_called_once()

    @pytest.mark.asyncio
    @patch("cortex.extensions.swarm.nightshift_daemon.discover", new_callable=AsyncMock)
    @patch("cortex.extensions.swarm.crystal_thermometer.scan_all_crystals", new_callable=AsyncMock)
    async def test_idle_cycle_no_targets(self, mock_scan, mock_discover, mock_db) -> None:
        """Test cycle when no targets are found by the radar."""
        mock_discover.return_value = []

        daemon = NightShiftCrystalDaemon(cortex_db=mock_db)
        report = await daemon.run_cycle()

        assert report["status"] == "idle"
        assert report["crystals"] == 0
        assert "consolidation" not in report  # Doesn't reach phase 2 if idle

        mock_discover.assert_called_once()
        mock_scan.assert_not_called()

    @pytest.mark.asyncio
    @patch("cortex.extensions.swarm.nightshift_daemon.discover", new_callable=AsyncMock)
    async def test_radar_failure(self, mock_discover, mock_db) -> None:
        """Test cycle handles radar exceptions gracefully."""
        mock_discover.side_effect = ValueError("Radar offline")

        daemon = NightShiftCrystalDaemon(cortex_db=mock_db)
        report = await daemon.run_cycle()

        assert report["status"] == "radar_failed"
        assert report["error"] == "Radar offline"

    @pytest.mark.asyncio
    @patch("cortex.extensions.swarm.nightshift_daemon.discover", new_callable=AsyncMock)
    @patch("cortex.extensions.swarm.nightshift_daemon.NightShiftPipeline.run", new_callable=AsyncMock)
    async def test_pipeline_failure(self, mock_run, mock_discover, mock_db) -> None:
        """Test cycle handles pipeline exceptions gracefully."""
        mock_discover.return_value = [{"type": "web"}]
        mock_run.side_effect = ValueError("Pipeline blown")

        daemon = NightShiftCrystalDaemon(cortex_db=mock_db)
        report = await daemon.run_cycle()

        assert report["status"] == "pipeline_failed"
        assert report["error"] == "Pipeline blown"

    @pytest.mark.asyncio
    @patch("cortex.extensions.swarm.nightshift_daemon.discover", new_callable=AsyncMock)
    @patch("cortex.extensions.swarm.nightshift_daemon.NightShiftPipeline.run", new_callable=AsyncMock)
    @patch("cortex.extensions.swarm.crystal_thermometer.scan_all_crystals", new_callable=AsyncMock)
    async def test_consolidation_failure_but_cycle_completes(
        self, mock_scan, mock_run, mock_discover, mock_db
    ) -> None:
        """Test that consolidation error doesn't completely fail the cycle report."""
        mock_discover.return_value = [{"type": "web"}]
        mock_run.return_value = {"crystals_count": 1}
        mock_scan.side_effect = ValueError("DB timeout during scan")

        daemon = NightShiftCrystalDaemon(cortex_db=mock_db)
        report = await daemon.run_cycle()

        assert report["status"] == "complete"
        assert "consolidation" in report
        assert report["consolidation"]["error"] == "DB timeout during scan"

    @pytest.mark.asyncio
    @patch(
        "cortex.extensions.swarm.nightshift_daemon.NightShiftCrystalDaemon.run_cycle", new_callable=AsyncMock
    )
    async def test_daemon_loop_cooldown(self, mock_run_cycle) -> None:
        """Verifies the daemon loop executes and respects the stop signal."""
        daemon = NightShiftCrystalDaemon(cooldown_hours=0.001)  # Very short cooldown

        # We need a task to run the daemon, and another to stop it
        async def run_daemon():
            await daemon.daemon_loop()

        task = asyncio.create_task(run_daemon())

        # Let it do at least one loop
        await asyncio.sleep(0.1)
        daemon.stop()

        await task

        # It should have run at least once, maybe more depending on timing
        assert mock_run_cycle.call_count >= 1
