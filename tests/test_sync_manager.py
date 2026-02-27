import json
from unittest.mock import Mock, patch

import pytest

from cortex.daemon.sync_manager import CortexSyncManager
from cortex.sync import SyncResult


@pytest.mark.asyncio
async def test_merkle_pulse_detection(tmp_path):
    """Test that MerklePulse correctly detects modified files."""
    mock_engine = Mock()

    sync_manager = CortexSyncManager(mock_engine)

    # Create a real memory dir with a test file
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    ghosts_file = mem_dir / "ghosts.json"
    ghosts_file.write_text(json.dumps([{"id": "1", "content": "hello"}]))

    # Patch MEMORY_DIR and file_hash + _run_sync_memory
    with patch("cortex.daemon.sync_manager.MEMORY_DIR", mem_dir, create=True):
        with patch("cortex.sync.common.MEMORY_DIR", mem_dir):
            # Mock the sync itself to return a SyncResult with total=1
            with patch.object(
                sync_manager,
                "_run_sync_memory",
                return_value=SyncResult(facts_synced=1),
            ):
                # 1. First sync — file exists, hash not in state → should sync
                result = await sync_manager._merkle_pulse_sync()
                assert result.total == 1

                # 2. Modify file — hash changes → should sync again
                ghosts_file.write_text(
                    json.dumps([{"id": "1", "content": "updated"}])
                )
                result2 = await sync_manager._merkle_pulse_sync()
                assert result2.total == 1

                # 3. No change → should return empty SyncResult (total=0)
                result3 = await sync_manager._merkle_pulse_sync()
                assert result3.total == 0
