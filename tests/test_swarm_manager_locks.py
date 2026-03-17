import asyncio

import pytest

from cortex.engine import CortexEngine
from cortex.engine.lock import SovereignLock
from cortex.extensions.swarm.manager import CapatazOrchestrator


@pytest.fixture
async def engine(tmp_path):
    """Provide a fresh CortexEngine for each test."""
    db_path = tmp_path / "test_swarm_lock.db"
    eng = CortexEngine(db_path=str(db_path))
    await eng.init_db()  # Initialize schema properly
    yield eng


@pytest.mark.asyncio
async def test_capataz_concurrent_execution_with_locks(engine: CortexEngine):
    """Verifiable test case proving simultaneous agent state mutation with locks via Capataz."""

    lock_manager = SovereignLock(engine)
    capataz = CapatazOrchestrator()
    resource = "swarm_shared_state"

    # Shared state
    shared_state = {"counter": 0}

    async def increment_task(agent_id: str, increments: int):
        for _ in range(increments):
            # Critical section inside the task itself is handled by Capataz wrapper
            current = shared_state["counter"]
            await asyncio.sleep(0.01)  # Simulate work and force context switch
            shared_state["counter"] = current + 1
        return shared_state["counter"]

    agents = [f"worker_{i}" for i in range(3)]
    increments_per_worker = 5

    # We define task objects for Capataz run_parallel
    task_definitions = []
    for agent_id in agents:
        task_definitions.append(
            {
                "name": f"task_{agent_id}",
                "agent_name": agent_id,
                "func": increment_task,
                "args": (agent_id, increments_per_worker),
                "lock_resource": resource,
                "lock_manager": lock_manager,
                "lock_timeout_s": 5.0,
            }
        )

    # Run them in parallel using Capataz
    results = await capataz.run_parallel(task_definitions)

    # Ensure no exceptions were returned instead of results
    for res in results:
        assert not isinstance(res, Exception), f"Task failed with exception: {res}"

    expected_total = len(agents) * increments_per_worker
    assert shared_state["counter"] == expected_total
