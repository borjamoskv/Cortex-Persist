import asyncio
import json
from unittest.mock import Mock, patch

import pytest

from cortex.daemon.sync_manager import CortexSyncManager


@pytest.mark.asyncio
async def test_merkle_pulse_detection(tmp_path):
    """Test that MerklePulse correctly detects modified files."""
    # 1. Setup mock engine and test directory
    mock_engine = Mock()
    mock_engine.recall_async = Mock()  # Return empty list by default

    sync_manager = CortexSyncManager(mock_engine)

    # Create a test file
    test_dir = tmp_path / "memory"
    test_dir.mkdir()
    test_file = test_dir / "fact_1.json"
    content = {"id": "1", "content": "hello"}
    test_file.write_text(json.dumps(content))

    # Mock engine.recall_async to return nothing (first sync)
    # Actually _merkle_pulse_sync calls engine.ingest_fact for each file

    # 2. Run first sync
    with patch("cortex.daemon.sync_manager.Path.iterdir", return_value=[test_file]):
        with patch("cortex.daemon.sync_manager.Path.is_file", return_value=True):
            # We need to mock the ingestion too
            mock_engine.ingest_fact = Mock(return_value=asyncio.Future())
            mock_engine.ingest_fact.return_value.set_result("ok")

            result = await sync_manager._merkle_pulse_sync()
            assert result.total == 1

            # 3. Modify file
            test_file.write_text(json.dumps({"id": "1", "content": "updated"}))

            # 4. Run second sync - should detect 1 change
            result2 = await sync_manager._merkle_pulse_sync()
            assert result2.total == 1

            # 5. Run third sync (no change) - should detect 0 changes
            result3 = await sync_manager._merkle_pulse_sync()
            assert result3.total == 0
