"""
Tests for SovereignLock (Axiom Ω₂).
Verifies lock-free acquisition and release via intent ledgers.
"""

import asyncio

import pytest

from cortex.engine import CortexEngine


@pytest.fixture
async def engine(tmp_path):
    db_path = tmp_path / "test_lock.db"
    engine = CortexEngine(str(db_path))
    await engine.init_db()
    yield engine
    await engine.close()


@pytest.mark.asyncio
async def test_sovereign_lock_lifecycle(engine):
    """Test basic acquire and release."""
    lock = engine.lock_sovereign

    # Acquire
    acquired = await lock.acquire("resource_1", "agent_A")
    assert acquired is True

    # Is locked?
    assert await lock.is_locked("resource_1") is True

    # Release
    await lock.release("resource_1", "agent_A")
    assert await lock.is_locked("resource_1") is False


@pytest.mark.asyncio
async def test_sovereign_lock_contention(engine):
    """Test that two agents cannot hold the same lock."""
    lock = engine.lock_sovereign

    # agent_A acquires
    await lock.acquire("resource_1", "agent_A")

    # agent_B tries to acquire (should fail/timeout)
    acquired_B = await lock.acquire("resource_1", "agent_B", timeout_s=1.0)
    assert acquired_B is False

    # agent_A releases
    await lock.release("resource_1", "agent_A")

    # agent_B tries again (should succeed)
    acquired_B_again = await lock.acquire("resource_1", "agent_B", timeout_s=1.0)
    assert acquired_B_again is True


@pytest.mark.asyncio
async def test_sovereign_lock_priority(engine):
    """Test that higher priority request jumps the queue."""
    lock = engine.lock_sovereign

    # agent_A holds the lock
    await lock.acquire("res", "agent_A")

    # agent_B requests with low priority
    task_B = asyncio.create_task(lock.acquire("res", "agent_B", priority=0, timeout_s=5))

    # agent_C requests with HIGH priority
    task_C = asyncio.create_task(lock.acquire("res", "agent_C", priority=10, timeout_s=5))

    await asyncio.sleep(0.5)  # Give time for intents to land

    # agent_A releases
    await lock.release("res", "agent_A")

    # agent_C should get it first because of priority 10 vs 0
    res_C = await task_C
    assert res_C is True

    # At this point, C holds it. B is still waiting.
    assert await lock.is_locked("res") is True
    cursor = await engine.session().execute(
        "SELECT holder_agent FROM lock_state WHERE resource = 'res'"
    )
    assert (await cursor.fetchone())[0] == "agent_C"

    # C releases
    await lock.release("res", "agent_C")

    # Now B should get it
    res_B = await task_B
    assert res_B is True
    assert (
        await (
            await engine.session().execute(
                "SELECT holder_agent FROM lock_state WHERE resource = 'res'"
            )
        ).fetchone()
    )[0] == "agent_B"
