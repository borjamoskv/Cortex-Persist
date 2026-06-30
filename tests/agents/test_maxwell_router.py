import pytest
import asyncio
from babylon60.agents.maxwell_router import create_maxwell_router
from babylon60.agents.bus import SqliteMessageBus
import uuid


def _uid():
    return f":memory:{uuid.uuid4().hex}:"


from babylon60.agents.message_schema import new_message, MessageKind


@pytest.mark.asyncio
async def test_maxwell_entropy_calculation():
    agent = create_maxwell_router("maxwell-test", SqliteMessageBus(db_path=_uid()))
    # Low entropy
    low = agent._calculate_shannon_entropy("fix typo in index.html")
    assert low < 0.8

    # High entropy
    high = agent._calculate_shannon_entropy(
        "Necesitamos diseñar la arquitectura BFT para la singularidad ultrathink"
    )
    assert high >= 0.8


@pytest.mark.asyncio
async def test_maxwell_routing():
    bus = SqliteMessageBus(db_path=_uid())
    agent = create_maxwell_router("maxwell-test", bus, entropy_threshold=0.8)

    # Verify initialization
    assert agent.manifest.agent_id == "maxwell-test"

    # Low entropy message routing
    msg_low = new_message(
        sender="user",
        recipient="maxwell-test",
        kind=MessageKind.TASK_REQUEST,
        payload={"prompt": "fix simple typo"},
    )

    await agent._handle_message(msg_low)

    # Drain low entropy routed message from bus
    low_messages = await bus.receive("flash_worker_01", timeout=0.5)
    assert low_messages is not None
    assert low_messages.recipient == "flash_worker_01"

    # High entropy message routing
    msg_high = new_message(
        sender="user",
        recipient="maxwell-test",
        kind=MessageKind.TASK_REQUEST,
        payload={
            "prompt": "Necesitamos diseñar la arquitectura BFT para la singularidad ultrathink"
        },
    )

    await agent._handle_message(msg_high)

    # Drain high entropy routed message from bus
    high_messages = await bus.receive("boltzmann_engine_01", timeout=0.5)
    assert high_messages is not None
    assert high_messages.recipient == "boltzmann_engine_01"
