# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch, ANY

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

from persistence import IdeStatePreserver


class TestIdeStatePreserver:
    @pytest.mark.asyncio
    @patch("persistence.ide_preserver.asyncio.create_subprocess_exec")
    @patch("persistence.ide_preserver.os.makedirs")
    @patch("persistence.ide_preserver.open")
    @patch("persistence.ide_preserver.hashlib.sha256")
    async def test_execute_snapshot_success(
        self, mock_sha256, mock_open, mock_makedirs, mock_create_subprocess
    ):
        # Mock ledger
        ledger = MagicMock()
        preserver = IdeStatePreserver(ledger)
        preserver.backup_dir = "/fake/backup"
        preserver.target_dir = "/fake/target"

        # Mock process
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = MagicMock(return_value=(b"stdout", b"stderr"))

        async def mock_communicate():
            return b"stdout", b"stderr"

        mock_proc.communicate = mock_communicate

        mock_create_subprocess.return_value = mock_proc

        # Mock sha256 hashing
        mock_hasher = MagicMock()
        mock_hasher.hexdigest.return_value = "abcdef1234567890" * 4
        mock_sha256.return_value = mock_hasher

        # Mock file reading (returns one chunk, then empty)
        mock_file = MagicMock()
        mock_file.read.side_effect = [b"chunk", b""]
        mock_open.return_value.__enter__.return_value = mock_file

        # Run snapshot execution
        await preserver._execute_snapshot_async()

        # Check directory creation
        mock_makedirs.assert_called_once_with("/fake/backup", exist_ok=True)

        # Check tar subprocess invocation
        mock_create_subprocess.assert_called_once_with(
            "/usr/bin/tar", "-czf", ANY, "--exclude=brain", "/fake/target", stdout=-1, stderr=-1
        )

        # Check ledger record registration
        ledger.append.assert_called_once()
        call_kwargs = ledger.append.call_args[1]
        assert call_kwargs["action"] == "IDE_STATE_SNAPSHOT"
        assert call_kwargs["vector_id"].startswith("hash:abcdef1234567890")
        assert call_kwargs["yield_amount"] == 0.0

    @pytest.mark.asyncio
    @patch("persistence.ide_preserver.asyncio.create_subprocess_exec")
    @patch("persistence.ide_preserver.logger")
    async def test_execute_snapshot_failure(self, mock_logger, mock_create_subprocess):
        # Setup subprocess run to fail
        mock_proc = MagicMock()
        mock_proc.returncode = 1

        async def mock_communicate():
            return b"", b"Tar command failed"

        mock_proc.communicate = mock_communicate

        mock_create_subprocess.return_value = mock_proc

        ledger = MagicMock()
        preserver = IdeStatePreserver(ledger)

        # Execute
        await preserver._execute_snapshot_async()

        # Check error was logged
        mock_logger.error.assert_called_once()
        assert "Failed to snapshot IDE state" in mock_logger.error.call_args[0][0]

        # Ledger shouldn't have been appended
        ledger.append.assert_not_called()

    @patch("persistence.ide_preserver.subprocess.run")
    @patch("persistence.ide_preserver.os.makedirs")
    def test_execute_snapshot_sync(self, mock_makedirs, mock_run):
        ledger = MagicMock()
        preserver = IdeStatePreserver(ledger)
        preserver.backup_dir = "/fake/backup"
        preserver.target_dir = "/fake/target"

        preserver._execute_snapshot_sync()

        mock_makedirs.assert_called_once_with("/fake/backup", exist_ok=True)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "/usr/bin/tar"
        assert args[1] == "-czf"
        assert "--exclude=brain" in args
