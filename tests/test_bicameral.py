import asyncio

import pytest

from cortex.engine import CortexEngine
from cortex.engine.bicameral import BicameralDispatcher


@pytest.mark.asyncio
async def test_bicameral_dispatch_logic():
    """Verify that the dispatcher separates concerns correctly."""
    dispatcher = BicameralDispatcher()

    fast_called = False
    slow_called = False

    async def mock_fast(*args, **kwargs):
        nonlocal fast_called
        fast_called = True
        return "fast_result"

    async def mock_slow(*args, **kwargs):
        nonlocal slow_called
        await asyncio.sleep(0.1) # Simulate IO
        slow_called = True

    dispatcher.register_fast("test_op", mock_fast)
    dispatcher.register_slow(mock_slow)

    # Execution
    result = await dispatcher.dispatch("test_op", "arg1")

    assert result == "fast_result"
    assert fast_called is True
    # Slow bus is backgrounded, might not be done immediately
    assert len(dispatcher._background_tasks) == 1

    await dispatcher.shutdown()
    assert slow_called is True

@pytest.mark.asyncio
async def test_engine_bicameral_integration():
    """Integration test for CortexEngine store delegation."""
    engine = CortexEngine()

    # We need to mock the slow-bus components to verify they are called
    slow_executed = asyncio.Event()

    async def mock_slow_callback(*args, **kwargs):
        # FactManager.store(project, content, ...)
        if "test_fact_long" in kwargs.get("content", "") or (len(args) > 1 and "test_fact_long" in args[1]):
            slow_executed.set()
        return 1

    async def mock_fast(*args, **kwargs):
        return "fast_ok"

    # Override the registered buses for 'store'
    engine.dispatcher.register_fast("store", mock_fast)
    engine.dispatcher._slow_bus["store"] = [mock_slow_callback]

    # Use 'content' as required by FactManager.store
    await engine.store("test_project", content="test_fact_long")

    # Wait for the background task
    try:
        await asyncio.wait_for(slow_executed.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("Slow bus was never executed for 'store'")
    finally:
        # The original_store was not captured in the new snippet, so we remove this line
        # engine.facts.store = original_store
        await engine.dispatcher.shutdown()
