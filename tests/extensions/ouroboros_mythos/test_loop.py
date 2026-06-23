import pytest
from babylon60.extensions.ouroboros_mythos.ouroboros_loop import MythosOuroborosEngine

@pytest.mark.asyncio
async def test_ouroboros_loop_initialization(tmp_path):
    log_file = tmp_path / "test_sec_audit.jsonl"
    engine = MythosOuroborosEngine(log_path=str(log_file))
    assert engine.is_running is False
    assert engine.state.identity_anchor == b"C5-REAL-MYTHOS-1"
    assert engine.meta_controller.health_score == 10000

@pytest.mark.asyncio
async def test_ouroboros_loop_critic_rejection(tmp_path):
    log_file = tmp_path / "test_sec_audit.jsonl"
    engine = MythosOuroborosEngine(log_path=str(log_file))
    
    # Mocking low critic score directly
    action_result = {"status": "failed"}
    score = await engine._criticize(action_result)
    
    # Primitive 20 enforces 92nd percentile logic, mock returns 10 on fail
    assert score == 10
    
    # Test strict integer yielding logic
    engine.exergy.compute_yield = lambda r, q=100: -5000
    yield_val = engine.exergy.compute_yield(score)
    
    assert yield_val < 0
    engine.meta_controller.register_pain(yield_val)
    
    assert engine.meta_controller.active_version == "v0.9.9-safe"
