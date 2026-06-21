import pytest
import asyncio
from cortex.extensions.ouroboros_mythos.ouroboros_loop import MythosOuroborosEngine

@pytest.mark.asyncio
async def test_ouroboros_loop_initialization():
    engine = MythosOuroborosEngine()
    assert engine.is_running is False
    assert engine.state.identity_anchor == "C5-REAL-MYTHOS-1"
    assert engine.meta_controller.health_score == 100.0

@pytest.mark.asyncio
async def test_ouroboros_loop_critic_rejection():
    engine = MythosOuroborosEngine()
    
    # Mocking low critic score directly
    action_result = {"status": "failed"}
    score = await engine._criticize(action_result)
    
    # Primitive 20 enforces 92nd percentile logic, mock returns 10 on fail
    assert score == 10
    
    # Calculate yield with mock exergy monitor (random Wh, so yield > 0 but low)
    # If we force exergy yield to be negative to test pain registration:
    engine.exergy.compute_yield = lambda r, q=1.0: -5.0
    yield_val = engine.exergy.compute_yield(score)
    
    assert yield_val < 0
    engine.meta_controller.register_pain(yield_val)
    
    assert engine.meta_controller.pain_accumulator == 5.0
