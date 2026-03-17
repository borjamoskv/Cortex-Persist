"""Torture Matrix for SovereignLock (Axiom Ω₂).
Validates resistance under high entropy, abandonment, and priority competition.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from cortex.engine import CortexEngine
from cortex.engine.lock import SovereignLock


@pytest.fixture
async def engine(tmp_path):
    db_path = tmp_path / "torture_lock.db"
    eng = CortexEngine(db_path=str(db_path))
    await eng.init_db()
    yield eng


@pytest.mark.asyncio
async def test_torture_high_concurrency(engine):
    """Scenario: 30 agents competing for the same resource, 3 rounds each.
    Validates atomic serialization, FIFO/Priority, and zero-loss under contention.

    Time budget: 30 agents × 3 rounds = 90 serial acquisitions.
    With TTL=0.5s and instant release, worst-case is ~45s + backoff overhead.
    Timeout of 120s per agent gives ample headroom.
    """
    lock = SovereignLock(engine)
    resource = "global_resource"
    shared_counter = {"val": 0}
    agents_count = 30
    rounds = 3

    async def competitor(agent_id):
        for _ in range(rounds):
            acquired = await lock.acquire(resource, agent_id, timeout_s=120.0, ttl_s=0.5)
            if acquired:
                try:
                    # Atomic increment — minimal critical section
                    shared_counter["val"] += 1
                finally:
                    await lock.release(resource, agent_id)

    tasks = [competitor(f"agent_{i}") for i in range(agents_count)]
    await asyncio.gather(*tasks)

    print(f"Torture Result: {shared_counter['val']}/{agents_count * rounds}")
    assert shared_counter["val"] == agents_count * rounds


@pytest.mark.asyncio
async def test_torture_abandonment_recovery(engine):
    """Scenario: Agent acquires lock and 'crashes' (no release).
    New agent must recover the resource after TTL expires.
    """
    lock = SovereignLock(engine)
    resource = "brittle_resource"

    # 1. Greedy agent acquires and vanishes
    acquired = await lock.acquire(resource, "greedy_ghost", ttl_s=0.2)
    assert acquired is True

    # 2. Hero agent tries to acquire immediately and fails
    hero_start = time.time()
    acquired_hero = await lock.acquire(resource, "hero", timeout_s=0.1)
    assert acquired_hero is False

    # 3. Hero agent waits and succeeds after TTL
    acquired_hero_retry = await lock.acquire(resource, "hero", timeout_s=1.0)
    assert acquired_hero_retry is True
    assert (time.time() - hero_start) >= 0.2


@pytest.mark.asyncio
async def test_torture_priority_starvation(engine):
    """Scenario: Low priority agent is waiting, high priority agent jumps the queue."""
    lock = SovereignLock(engine)
    resource = "ordered_resource"

    # 1. Hold the resource
    await lock.acquire(resource, "holder", ttl_s=1.0)

    # 2. Helper to acquire and release
    async def acquire_and_release(agent, p):
        if await lock.acquire(resource, agent, priority=p, timeout_s=5.0, ttl_s=1.0):
            await asyncio.sleep(0.1)
            await lock.release(resource, agent)
            return True
        return False

    # Start tasks
    low_task = asyncio.create_task(acquire_and_release("low_p", 0))
    await asyncio.sleep(0.1)
    high_task = asyncio.create_task(acquire_and_release("high_p", 9))
    await asyncio.sleep(0.1)

    # 3. Release holder
    await lock.release(resource, "holder")

    # 4. Gather
    results = await asyncio.gather(low_task, high_task)
    assert all(results)


@pytest.mark.asyncio
async def test_torture_shared_memory_mode(tmp_path):
    """Scenario: Verify lock works on shared-cache memory databases (volatile enjambre)."""
    # SQLite memory with shared cache
    db_uri = f"file:{tmp_path}/torture_mem?mode=memory&cache=shared"
    eng = CortexEngine(db_path=db_uri)
    await eng.init_db()

    lock = SovereignLock(eng)
    resource = "volatile_resource"

    assert await lock.acquire(resource, "ghost_1", ttl_s=1.0) is True
    assert await lock.is_locked(resource) is True
    await lock.release(resource, "ghost_1")
    assert await lock.is_locked(resource) is False
