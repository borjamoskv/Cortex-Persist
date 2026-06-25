import pytest
import asyncio
from cortex.engine.ouroboros_daemon import OuroborosDaemon

@pytest.mark.asyncio
async def test_ouroboros_sweep_wal_purges_old_nodes():
    daemon = OuroborosDaemon(check_interval_seconds=1.0, decay_threshold_ms=100.0)
    
    current_time = 500.0
    daemon.record_access("node_recent", current_time - 50.0)
    daemon.record_access("node_old", current_time - 150.0)
    
    purged_count = await daemon.sweep_wal(current_time)
    
    assert purged_count == 1
    assert "node_recent" in daemon._node_access_times
    assert "node_old" not in daemon._node_access_times

@pytest.mark.asyncio
async def test_ouroboros_daemon_lifecycle():
    daemon = OuroborosDaemon(check_interval_seconds=0.01)
    await daemon.start()
    assert daemon._running is True
    assert daemon._task is not None
    
    await daemon.stop()
    assert daemon._running is False
    assert daemon._task is None
