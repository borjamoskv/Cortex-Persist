import os
import json
import pytest
import asyncio
from babylon60.api.fsm_streamer import ledger_byte_watcher

class MockRequest:
    def __init__(self):
        self.calls = 0

    async def is_disconnected(self) -> bool:
        self.calls += 1
        # Stop after 2 ticks to prevent infinite loops in tests
        return self.calls > 2

@pytest.mark.asyncio
async def test_ledger_byte_watcher(tmp_path):
    """
    Direct unit test for the ledger_byte_watcher async generator.
    Avoids Starlette TestClient SSE deadlocks by testing the generator logic directly.
    """
    # Setup tmp AOF file
    aof_file = tmp_path / "cortex_state.aof"
    os.environ["CORTEX_LEDGER_PATH"] = str(aof_file)
    
    # Write initial node mutation
    node_1 = {"hash_id": "node_1", "state": "proposed", "exergy": 100}
    with open(aof_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(node_1) + "\n")
        
    request = MockRequest()
    events = []
    
    # Consume from the async generator
    async for event in ledger_byte_watcher(request, poll_interval=0.01):
        events.append(event)
        
    assert len(events) >= 1
    first_event = events[0]
    assert first_event["event"] == "state_mutation"
    assert first_event["id"] == "node_1"
    
    data = json.loads(first_event["data"])
    assert data["state"] == "proposed"
    assert data["exergy"] == 100

    # Clean up env var
    os.environ.pop("CORTEX_LEDGER_PATH", None)
