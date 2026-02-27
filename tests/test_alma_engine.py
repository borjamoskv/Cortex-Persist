from unittest.mock import MagicMock

import pytest

from cortex.alma.engine import AlmaEngine
from cortex.telemetry.metrics import metrics


@pytest.mark.asyncio
async def test_alma_engine_pulse_dormant():
    """Verify state when there is no system activity."""
    # Mock Memory Manager
    mock_memory = MagicMock()
    mock_memory._background_tasks = []
    
    # Reset metrics
    metrics.reset()
    
    engine = AlmaEngine(mock_memory)
    state = await engine.pulse()
    
    assert state.vibe == "dormant"
    assert state.anxiety == 0.0
    assert state.energy == 0.0

@pytest.mark.asyncio
async def test_alma_engine_pulse_chaotic():
    """Verify state when there are multiple ledger violations."""
    mock_memory = MagicMock()
    mock_memory._background_tasks = []
    
    metrics.reset()
    # Inject 5 ledger violations (threshold for chaotic start)
    metrics.inc("cortex_ledger_violations_total", value=5)
    
    engine = AlmaEngine(mock_memory)
    state = await engine.pulse()
    
    assert state.anxiety >= 0.7
    assert state.vibe == "chaotic"

@pytest.mark.asyncio
async def test_alma_engine_pulse_focused():
    """Verify state when there is high throughput but no errors."""
    mock_memory = MagicMock()
    mock_memory._background_tasks = [MagicMock()] * 5 # 5 active tasks
    
    metrics.reset()
    metrics.inc("cortex_http_requests_total", value=50) # 50 requests
    
    # Mock synergy (uptime)
    metrics.inc("cortex_http_requests_total", labels={"status": "200"}, value=50)
    
    engine = AlmaEngine(mock_memory)
    state = await engine.pulse()
    
    assert state.energy >= 0.4
    assert state.anxiety == 0.0
    assert state.vibe == "focused"


@pytest.mark.asyncio
async def test_alma_engine_smoothing():
    """Verify that states transition fluidly via EMA."""
    mock_memory = MagicMock()
    mock_memory._background_tasks = []
    
    metrics.reset()
    engine = AlmaEngine(mock_memory)
    
    # Pulse 1: Intense anxiety
    metrics.inc("cortex_ledger_violations_total", value=5)
    state1 = await engine.pulse()
    
    # Pulse 2: Instantly fixed, but smoothing should keep anxiety high for a bit
    metrics.reset()
    state2 = await engine.pulse()
    
    assert state2.anxiety < state1.anxiety
    assert state2.anxiety > 0.5 # EMA smoothing (0.8 * 1.0 + 0.2 * 0.0 = 0.8)
    assert state2.vibe == "chaotic" # Still chaotic due to trauma/memory
