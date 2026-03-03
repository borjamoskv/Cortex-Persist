from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cortex.cli.session_cmds import logout_cmd


@pytest.fixture
def runner():
    return CliRunner()


def test_logout_no_changes(runner):
    """Test logout succeeds when no changes are detected."""
    with (
        patch("cortex.cli.session_cmds._get_uncommitted_changes", return_value=[]),
        patch("cortex.cli.session_cmds.get_engine"),
        patch("cortex.cli.session_cmds.close_engine_sync"),
    ):
        result = runner.invoke(logout_cmd)
        assert result.exit_code == 0
        assert "Session closed cleanly" in result.output


def test_logout_with_changes_and_recent_decision(runner):
    """Test logout succeeds when changes exist but a recent decision is found."""
    with (
        patch("cortex.cli.session_cmds._get_uncommitted_changes", return_value=["M file.py"]),
        patch("cortex.cli.session_cmds._has_recent_decision", return_value=True),
        patch("cortex.cli.session_cmds.get_engine"),
        patch("cortex.cli.session_cmds.close_engine_sync"),
    ):
        result = runner.invoke(logout_cmd)
        assert result.exit_code == 0
        assert "Session closed cleanly" in result.output


def test_logout_blocked_by_entropy_no_decision(runner):
    """Test logout is rejected when changes exist and no recent decision is found."""
    with (
        patch("cortex.cli.session_cmds._get_uncommitted_changes", return_value=["M file.py"]),
        patch("cortex.cli.session_cmds._has_recent_decision", return_value=False),
        patch("cortex.cli.session_cmds.get_engine"),
        patch("cortex.cli.session_cmds.close_engine_sync"),
    ):
        result = runner.invoke(logout_cmd)
        assert result.exit_code == 1
        assert "IMMUNE BLOCK" in result.output
        assert "Unaccounted entropy changes detected" in result.output


def test_logout_force_bypass(runner):
    """Test logout --force bypasses the block."""
    with (
        patch("cortex.cli.session_cmds._get_uncommitted_changes", return_value=["M file.py"]),
        patch("cortex.cli.session_cmds._has_recent_decision", return_value=False),
        patch("cortex.cli.session_cmds.get_engine"),
        patch("cortex.cli.session_cmds.close_engine_sync"),
    ):
        result = runner.invoke(logout_cmd, ["--force"])
        assert result.exit_code == 0
        assert "Forcing logout" in result.output


def test_has_recent_decision_logic():
    """Test the internal _has_recent_decision logic with mocked DB."""
    from cortex.cli.session_cmds import _has_recent_decision

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine._get_sync_conn.return_value = mock_conn

    # Case 1: No decision at all
    mock_conn.execute.return_value.fetchone.return_value = None
    assert _has_recent_decision(mock_engine) is False

    # Case 2: Very recent decision
    recent_time = datetime.now().isoformat()
    mock_conn.execute.return_value.fetchone.return_value = [recent_time]
    assert _has_recent_decision(mock_engine, minutes=60) is True

    # Case 3: Old decision (2 hours ago)
    old_time = (datetime.now() - timedelta(hours=2)).isoformat()
    mock_conn.execute.return_value.fetchone.return_value = [old_time]
    assert _has_recent_decision(mock_engine, minutes=60) is False


def test_get_uncommitted_changes_git_mock():
    """Test git status parsing."""
    from cortex.cli.session_cmds import _get_uncommitted_changes

    with patch("subprocess.run") as mock_run:
        # Mock successful git status
        mock_run.return_value = MagicMock(returncode=0, stdout=" M file1.py\n?? file2.py\n")
        changes = _get_uncommitted_changes()
        assert len(changes) == 2
        assert "M file1.py" in changes
        assert "?? file2.py" in changes

        # Mock failed git status
        mock_run.return_value = MagicMock(returncode=128)
        assert _get_uncommitted_changes() == []
