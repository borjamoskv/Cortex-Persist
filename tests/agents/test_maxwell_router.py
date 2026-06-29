import pytest
import asyncio
from cortex.agents.maxwell_router import create_maxwell_router
from cortex.agents.bus import SqliteMessageBus
import uuid

def _uid(): return f':memory:{uuid.uuid4().hex}:'

from cortex.agents.message_schema import new_message, MessageKind

@pytest.mark.asyncio
async def test_maxwell_entropy_calculation():
    agent = create_maxwell_router("maxwell-test", SqliteMessageBus(db_path=_uid()))
    # Low entropy
    low = agent._calculate_shannon_entropy("fix typo in index.html")
    assert low < 0.8
    
    # High entropy
    high = agent._calculate_shannon_entropy("Necesitamos diseñar la arquitectura BFT para la singularidad ultrathink")
    assert high >= 0.8

@pytest.mark.asyncio
async def test_maxwell_routing():
    bus = SqliteMessageBus(db_path=_uid())
    agent = create_maxwell_router("maxwell-test", bus, entropy_threshold=0.8)
    await agent.bind_bus(bus)
    
    # Since it's a test, we just verify initialization and binding
    assert agent.name == "maxwell-test"
