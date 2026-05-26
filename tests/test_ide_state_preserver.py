"""Tests for IdeStatePreserver in cortex-core/persistence.py."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

from persistence import IdeStatePreserver


class TestIdeStatePreserver:
    @patch("persistence.subprocess.run")
    @patch("persistence.os.makedirs")
    @patch("persistence.open")
    @patch("persistence.hashlib.sha256")
    def test_execute_snapshot_success(self, mock_sha256, mock_open, mock_makedirs, mock_run):
        # Mock ledger
        ledger = MagicMock()
        preserver = IdeStatePreserver(ledger)
        preserver.backup_dir = "/fake/backup"
        preserver.target_dir = "/fake/target"

        # Mock sha256 hashing
        mock_hasher = MagicMock()
        mock_hasher.hexdigest.return_value = "abcdef1234567890" * 4
        mock_sha256.return_value = mock_hasher

        # Mock file reading (returns one chunk, then empty)
        mock_file = MagicMock()
        mock_file.read.side_effect = [b"chunk", b""]
        mock_open.return_value.__enter__.return_value = mock_file

        # Run snapshot execution
        preserver._execute_snapshot()

        # Check directory creation
        mock_makedirs.assert_called_once_with("/fake/backup", exist_ok=True)

        # Check tar subprocess invocation
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0].endswith("tar")
        assert args[1] == "-czf"
        assert "--exclude=brain" in args
        assert "/fake/target" in args

        # Check ledger record registration
        ledger.append.assert_called_once()
        call_kwargs = ledger.append.call_args[1]
        assert call_kwargs["action"] == "IDE_STATE_SNAPSHOT"
        assert call_kwargs["vector_id"].startswith("hash:abcdef1234567890")
        assert call_kwargs["yield_amount"] == 0.0

    @patch("persistence.subprocess.run")
    @patch("persistence.logger")
    def test_execute_snapshot_failure(self, mock_logger, mock_run):
        # Setup subprocess run to fail
        mock_run.side_effect = Exception("Tar command failed")
        ledger = MagicMock()
        preserver = IdeStatePreserver(ledger)

        # Execute
        preserver._execute_snapshot()

        # Check error was logged
        mock_logger.error.assert_called_once()
        assert "Failed to snapshot IDE state" in mock_logger.error.call_args[0][0]

        # Ledger shouldn't have been appended
        ledger.append.assert_not_called()
