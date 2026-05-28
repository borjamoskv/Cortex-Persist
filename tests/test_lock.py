"""Tests for SovereignLock — Ω₂ Lock-Free Concurrency."""

import asyncio

import pytest

from cortex.engine import CortexEngine
from cortex.engine.lock import SovereignLock


@pytest.fixture
async def engine(tmp_path):
    """Provide a fresh CortexEngine for each test."""
    db_path = tmp_path / "test_lock.db"
    eng = CortexEngine(db_path=str(db_path))
    await eng.init_db()  # Initialize schema properly
    yield eng


@pytest.mark.asyncio
async def test_sovereign_lock_acquisition(engine: CortexEngine):
    """Test basic lock acquisition and release."""
    lock = SovereignLock(engine)
    resource = "test_resource"
    agent_id = "agent_1"

    # Acquire lock
    acquired = await lock.acquire(resource, agent_id, timeout_s=1.0)
    assert acquired is True
    assert await lock.is_locked(resource) is True

    # Release lock
    await lock.release(resource, agent_id)
    # Wait for background _reduce_resource if it takes time, but in this implementation it's somewhat synchronous
    await asyncio.sleep(0.1)  # Give time for reduction
    assert await lock.is_locked(resource) is False


@pytest.mark.asyncio
async def test_sovereign_lock_mutual_exclusion(engine: CortexEngine):
    """Test that two agents cannot hold the lock simultaneously."""
    lock = SovereignLock(engine)
    resource = "shared_resource"

    # Agent A acquires
    acquired_a = await lock.acquire(resource, "agent_A", timeout_s=1.0)
    assert acquired_a is True

    # Agent B tries to acquire and fails (times out)
    acquired_b = await lock.acquire(resource, "agent_B", timeout_s=0.5)
    assert acquired_b is False

    # Agent A releases
    await lock.release(resource, "agent_A")
    await asyncio.sleep(0.1)

    # Agent B can now acquire
    acquired_b_retry = await lock.acquire(resource, "agent_B", timeout_s=1.0)
    assert acquired_b_retry is True


@pytest.mark.asyncio
async def test_sovereign_lock_concurrent_contention(engine: CortexEngine):
    """Test concurrent agents trying to mutate state safely using locks."""
    lock = SovereignLock(engine)
    resource = "high_contention_resource"

    # We will simulate a shared state that agents try to increment.
    # Without locks, this would lead to race conditions.
    # Note: We are simulating state in memory just for the test,
    # the lock ensures only one agent modifies it at a time.
    shared_state = {"counter": 0}

    async def agent_task(agent_id: str, increments: int):
        for _ in range(increments):
            # Try to acquire, waiting up to 5 seconds
            acquired = await lock.acquire(resource, agent_id, timeout_s=5.0)
            if acquired:
                try:
                    # Critical section
                    current = shared_state["counter"]
                    # Simulate some async work that might cause context switches
                    await asyncio.sleep(0.01)
                    shared_state["counter"] = current + 1
                finally:
                    await lock.release(resource, agent_id)

    # Launch 5 agents, each incrementing 10 times
    agents = [f"agent_{i}" for i in range(5)]
    increments_per_agent = 10

    tasks = [asyncio.create_task(agent_task(agent_id, increments_per_agent)) for agent_id in agents]

    await asyncio.gather(*tasks)

    # The final counter should be agents * increments
    expected_total = len(agents) * increments_per_agent
    assert shared_state["counter"] == expected_total


@pytest.mark.asyncio
async def test_sovereign_lock_ttl_expiration(engine: CortexEngine):
    """Test that a lock expires if held past its TTL."""
    lock = SovereignLock(engine)
    resource = "ttl_resource"

    # Acquire with a very short TTL
    acquired = await lock.acquire(resource, "greedy_agent", timeout_s=1.0, ttl_s=0.5)
    assert acquired is True

    assert await lock.is_locked(resource) is True

    # Wait for TTL to expire
    await asyncio.sleep(0.6)

    # Check that it's no longer locked (is_locked handles TTL logic)
    assert await lock.is_locked(resource) is False

    # Another agent can now acquire it without the first explicitly releasing
    acquired_b = await lock.acquire(resource, "patient_agent", timeout_s=1.0)
    assert acquired_b is True
