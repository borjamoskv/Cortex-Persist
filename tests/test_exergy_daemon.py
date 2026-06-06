# [C5-REAL] Exergy-Maximized

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))
import cortex.core.config as config
from exergy_daemon import ExergyDaemon


@pytest.mark.asyncio
async def test_exergy_daemon_init():
    """Test initializing the ExergyDaemon class."""
    daemon = ExergyDaemon(check_interval=10)
    assert daemon.check_interval == 10
    assert daemon.is_running is True


@pytest.mark.asyncio
async def test_exergy_daemon_auto_heal_code():
    """Test auto-healing code execution (mocked)."""
    daemon = ExergyDaemon(check_interval=10)
    daemon.ruff_cmd = "/usr/bin/ruff"

    mock_process = MagicMock()
    mock_process.communicate = AsyncMock(return_value=(b"fixed", b""))
    mock_process.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
        await daemon.auto_heal_code()
        assert mock_exec.call_count == 2  # check --fix and format


@pytest.mark.asyncio
async def test_exergy_daemon_auto_heal_db():
    """Test database hygiene execution."""
    daemon = ExergyDaemon(check_interval=10)

    mock_conn = MagicMock()
    with patch("sqlite3.connect", return_value=mock_conn) as mock_connect:
        await daemon.auto_heal_db()
        mock_connect.assert_called_once()
        mock_conn.execute.assert_any_call("PRAGMA wal_checkpoint(TRUNCATE);")
        mock_conn.execute.assert_any_call("VACUUM;")
        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_exergy_daemon_auto_heal_playwright():
    """Test playwright cleanup execution (mocked)."""
    daemon = ExergyDaemon(check_interval=10)

    mock_pgrep = MagicMock()
    mock_pgrep.communicate = AsyncMock(return_value=(b"1234\n5678", b""))
    mock_pgrep.returncode = 0

    mock_pkill = MagicMock()
    mock_pkill.communicate = AsyncMock(return_value=(b"", b""))
    mock_pkill.returncode = 0

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_pgrep, mock_pkill]) as mock_exec:
        await daemon.auto_heal_playwright()
        assert mock_exec.call_count == 2


@pytest.mark.asyncio
async def test_exergy_daemon_perform_health_assessment():
    """Test health assessment logic and db persistence."""
    daemon = ExergyDaemon(check_interval=10)

    mock_metric = MagicMock()
    mock_metric.name = "test_metric"
    mock_metric.value = 0.95
    mock_metric.description = "Test metric description"

    mock_score = MagicMock()
    mock_score.score = 95.0
    mock_score.grade.letter = "A"
    mock_score.metrics = [mock_metric]

    mock_collector = MagicMock()
    mock_collector.collect_all.return_value = [mock_metric]

    with (
        patch("exergy_daemon.HealthCollector", return_value=mock_collector),
        patch("exergy_daemon.HealthScorer.score", return_value=mock_score),
        patch("exergy_daemon.TrendDetector") as mock_trend_cls,
    ):
        mock_trend = mock_trend_cls.return_value
        score = await daemon.perform_health_assessment()

        assert score == 95.0
        mock_collector.collect_all.assert_called_once()
        mock_trend.push.assert_called_once_with(95.0)
        mock_trend.persist_to_db.assert_called_once()
        mock_trend.prune_history.assert_called_once_with(config.DB_PATH, keep_days=30)
