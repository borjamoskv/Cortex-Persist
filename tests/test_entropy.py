"""Tests for ENTROPY-0 monitor and alerts."""

from unittest.mock import MagicMock, patch

from cortex.daemon.core import MoskvDaemon
from cortex.daemon.models import DaemonStatus, EntropyAlert
from cortex.daemon.monitors import EntropyMonitor


def test_entropy_monitor_no_projects():
    """Test EntropyMonitor with no projects."""
    monitor = EntropyMonitor(projects={}, interval_seconds=1800, threshold=90)
    alerts = monitor.check()
    assert len(alerts) == 0


@patch("cortex.mejoralo.MejoraloEngine")
@patch("cortex.engine.CortexEngine")
def test_entropy_monitor_with_violations(mock_engine, mock_mejoralo, tmp_path):
    """Test EntropyMonitor detects high entropy."""
    # Setup mocks
    mock_m = mock_mejoralo.return_value
    mock_result = MagicMock()
    mock_result.score = 50  # Below 90 threshold
    mock_m.scan.return_value = mock_result

    # Run check
    monitor = EntropyMonitor(
        projects={"my-project": str(tmp_path)}, threshold=90, interval_seconds=0
    )
    alerts = monitor.check()

    assert len(alerts) == 1
    assert isinstance(alerts[0], EntropyAlert)
    assert alerts[0].project == "my-project"
    assert alerts[0].complexity_score == 50
    assert "Entropía detectada: 50/90" in alerts[0].message


@patch("cortex.mejoralo.MejoraloEngine")
@patch("cortex.engine.CortexEngine")
def test_entropy_monitor_no_violations(mock_engine, mock_mejoralo, tmp_path):
    """Test EntropyMonitor passes clean projects."""
    mock_m = mock_mejoralo.return_value
    mock_result = MagicMock()
    mock_result.score = 95  # Above 90 threshold
    mock_m.scan.return_value = mock_result

    monitor = EntropyMonitor(
        projects={"my-project": str(tmp_path)}, threshold=90, interval_seconds=0
    )
    alerts = monitor.check()

    assert len(alerts) == 0


@patch("cortex.daemon.notifier.Notifier.notify")
@patch("subprocess.Popen")
def test_daemon_alert_entropy_brutal(mock_popen, mock_notify, tmp_path):
    """Test MoskvDaemon triggers /mejoralo --brutal on critical entropy."""
    daemon = MoskvDaemon(notify=True, config_dir=tmp_path)
    daemon._cooldown = 0

    # Critical alert (< 30)
    alerts = [
        EntropyAlert(
            project="critical-project",
            file_path="/fake/path",
            complexity_score=25,
            message="Critical",
        )
    ]

    daemon._alert_entropy(alerts)

    # Check Notifier was called properly
    mock_notify.assert_called_with(
        "☢️ PURGA DE ENTROPÍA (Score < 30)",
        "critical-project: Invocando /mejoralo --brutal automáticamente.",
        sound="Basso",
    )

    # Check Popen was called
    assert mock_popen.called
    args = mock_popen.call_args[0][0]
    assert "mejoralo" in args
    assert "scan" in args
    assert "--brutal" in args


@patch("cortex.daemon.notifier.Notifier.notify")
@patch("subprocess.Popen")
def test_daemon_alert_entropy_warning(mock_popen, mock_notify, tmp_path):
    """Test MoskvDaemon logs warning for high but non-critical entropy."""
    daemon = MoskvDaemon(notify=True, config_dir=tmp_path)
    daemon._cooldown = 0

    # Warning alert (< 90 but > 30)
    alerts = [
        EntropyAlert(
            project="warning-project",
            file_path="/fake/path",
            complexity_score=75,
            message="Warning",
        )
    ]

    daemon._alert_entropy(alerts)

    # Check Notifier was called with warning
    mock_notify.assert_called_with(
        "⚠️ Alerta de Entropía", "warning-project score 75. Cuidado.", sound="Basso"
    )

    # Check Popen was NOT called (no brutal mode)
    assert not mock_popen.called


def test_daemon_status_serialization():
    """Test DaemonStatus properly serializes EntropyAlert."""
    status = DaemonStatus(checked_at="2024-01-01T00:00:00Z")
    status.entropy_alerts = [
        EntropyAlert(project="test", file_path="/test", complexity_score=50, message="Test message")
    ]

    data = status.to_dict()
    assert "entropy_alerts" in data
    assert len(data["entropy_alerts"]) == 1
    assert data["entropy_alerts"][0]["project"] == "test"
    assert data["entropy_alerts"][0]["complexity_score"] == 50
