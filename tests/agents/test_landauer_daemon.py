import pytest
import asyncio
from cortex.agents.bus import SqliteMessageBus
import uuid

def _uid(): return f':memory:{uuid.uuid4().hex}:'
from cortex.agents.landauer_daemon import create_landauer_daemon

@pytest.mark.asyncio
async def test_landauer_daemon_lifecycle():
    agent = create_landauer_daemon("landauer-test", SqliteMessageBus(db_path=_uid()), compaction_interval_seconds=0.1)
    
    assert agent.manifest.agent_id == "landauer-test"
    assert agent._daemon_task is None
    
    await agent.start()
    assert agent._daemon_task is not None
    assert not agent._daemon_task.done()
    
    await asyncio.sleep(0.15) # Wait for at least one loop
    
    await agent.stop()
    assert agent._daemon_task is None
