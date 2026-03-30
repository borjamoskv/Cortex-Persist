import pytest
import asyncio
from cortex.engine.legion import KVRouter, LegionOmegaEngine

@pytest.mark.asyncio
async def test_kv_router_caching():
    router = KVRouter()
    prefix = "SYSTEM: Test Prefix"
    state1 = "State 1"
    state2 = "State 2"
    
    # First call: COLD
    res1 = router.route(prefix, state1)
    assert "[COLD:" in res1
    
    # Second call: WARM
    res2 = router.route(prefix, state2)
    assert "[WARM:" in res2
    assert "State 2" in res2

@pytest.mark.asyncio
async def test_engine_integration_metrics():
    engine = LegionOmegaEngine(max_cycles=2)
    result = await engine.forge("test_intent")
    
    assert hasattr(result, "exergy")
    assert hasattr(result, "entropy_delta")
    assert hasattr(result, "yield_hours")
    assert result.exergy >= 0.0
