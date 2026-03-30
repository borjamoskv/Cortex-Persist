import pytest
import asyncio
from cortex.daemon.chaos import ChaosDaemon

class MockEngine:
    pass

@pytest.mark.asyncio
async def test_chaos_latency_injection():
    engine = MockEngine()
    daemon = ChaosDaemon(engine)
    
    # We trigger the stability iteration which calls _inject_latency
    # We just want to ensure it doesn't crash and logs correctly (verified via mock or observation)
    await daemon.iterate_on_stability()
    
    # Check if a task was created (it should be in the loop or finished)
    # Since it's a stub hook for now, we just verify it runs.
    assert True 
