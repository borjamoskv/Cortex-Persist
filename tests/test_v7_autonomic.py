from unittest.mock import MagicMock

import pytest

from cortex.memory.semantic_ram import AutonomicMemoryBuffer, DynamicSemanticSpace


@pytest.mark.asyncio
async def test_autonomic_buffer_capacity():
    buffer = AutonomicMemoryBuffer(capacity=2)
    assert await buffer.add({"id": 1})
    assert await buffer.add({"id": 2})
    assert not await buffer.add({"id": 3})


@pytest.mark.asyncio
async def test_autonomic_buffer_flush():
    buffer = AutonomicMemoryBuffer(capacity=10)
    await buffer.add({"id": 1})
    await buffer.add({"id": 2})

    data = await buffer.flush()
    assert len(data) == 2
    assert len(await buffer.flush()) == 0


@pytest.mark.asyncio
async def test_dynamic_space_heartbeat_store():
    # Mock store
    store = MagicMock()
    space = DynamicSemanticSpace(store=store, buffer_capacity=5)

    success = await space.store_with_heartbeat("test_proj", "test_content")
    assert success

    buffer_data = await space.autonomic_buffer.flush()
    assert len(buffer_data) == 1
    assert buffer_data[0]["project"] == "test_proj"
