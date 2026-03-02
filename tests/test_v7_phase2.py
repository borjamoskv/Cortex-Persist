import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.rem_cycle import REMCoordinator

@pytest.mark.asyncio
async def test_endocrine_pulse():
    # Reset to baseline
    current_cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)
    ENDOCRINE.pulse(HormoneType.CORTISOL, -current_cortisol + 0.1)
    
    # Pulse up
    new_val = ENDOCRINE.pulse(HormoneType.CORTISOL, 0.2)
    assert new_val == pytest.approx(0.3)
    
    # Clamp check
    clamped = ENDOCRINE.pulse(HormoneType.CORTISOL, 1.5)
    assert clamped == 1.0

@pytest.mark.asyncio
async def test_rem_coordinator_execution():
    conn = MagicMock()
    # Mock the reaper and decalcifier to succeed
    coordinator = REMCoordinator(conn)
    coordinator._reaper.reap_db_ghosts = AsyncMock(return_value=5)
    coordinator._decalcifier.decalcify_cycle = AsyncMock(return_value=10)
    
    await coordinator.enter_rem()
    
    coordinator._reaper.reap_db_ghosts.assert_called_once_with(conn)
    coordinator._decalcifier.decalcify_cycle.assert_called_once_with(conn)
    assert coordinator.is_active is False

@pytest.mark.asyncio
async def test_endocrine_balance():
    balance = ENDOCRINE.balance
    assert "CORTISOL" in balance
    assert "NEURAL_GROWTH" in balance
    assert isinstance(balance["CORTISOL"], float)
