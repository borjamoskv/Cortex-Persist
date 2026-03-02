import asyncio
import pytest
import time
from cortex.memory.semantic_ram import AutonomicMemoryBuffer, DynamicSemanticSpace
from cortex.engine.apotheosis import ApotheosisEngine
from pathlib import Path

@pytest.mark.asyncio
async def test_semantic_pressure_autoflush():
    """Verify that Semantic RAM flushes automatically when pressure is high."""
    buffer = AutonomicMemoryBuffer(capacity=10, pressure_threshold=0.5)
    
    # Add 4 facts (40% pressure) -> no flush trigger
    for i in range(4):
        needs_flush = await buffer.add({"fact": i})
        assert needs_flush is False
        
    # Add 5th fact (50% pressure) -> trigger
    needs_flush = await buffer.add({"fact": 5})
    assert needs_flush is True

@pytest.mark.asyncio
async def test_predictive_inertia_calculation():
    """Verify that ApotheosisEngine calculates cognitive weight based on actions."""
    from unittest.mock import patch, MagicMock
    
    class MockAction:
        def __init__(self, value):
            self.value = value
            self.description = "mock"
            self.action_type = "mock"

    with patch("cortex.policy.PolicyEngine") as MockPolicy:
        mock_instance = MockPolicy.return_value
        mock_instance.evaluate = asyncio.iscoroutinefunction(lambda: None) # placeholder
        mock_instance.evaluate = MagicMock(return_value=asyncio.Future())
        mock_instance.evaluate.return_value.set_result([MockAction(0.9), MockAction(0.8)])
        
        engine = ApotheosisEngine(Path("/tmp"), cortex_engine=MagicMock())
        await engine._policy_pulse()
        
        # (0.9 + 0.8) / 2 = 0.85
        assert engine._cognitive_weight == pytest.approx(0.85)
        assert engine._cognitive_weight > engine._inertia_threshold

if __name__ == "__main__":
    pytest.main([__file__])
