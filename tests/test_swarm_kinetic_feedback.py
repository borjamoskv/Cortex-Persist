# [C5-REAL] Exergy-Maximized
import asyncio

import pytest

from cortex.engine.swarm.swarm_10k import CenturionSuperv, SwarmCommander


@pytest.mark.asyncio
async def test_swarm_kinetic_feedback_throttling(tmp_path):
    """
    Verify Singularity v7.0 - Throttling triggers when exergy is low.
    """
    cmd = SwarmCommander(tmp_path)
    await cmd.initialize()

    # Create a legion
    legion = await cmd.get_or_create_legion("thermal-test")
    cen = await legion.ensure_centurion()

    # 1. Force low exergy on the centurion
    # Simulate 95% capacity
    for i in range(95):
        cen.agents.append(f"ag-{i}")
    cen.metrics.active_children = 95
    cen.last_latency_ms = 48.0  # Breach

    exergy = await cen.get_exergy()
    assert exergy < 0.7  # Should trigger throttling

    # 2. Try bucketed dispatch
    tasks = [{"domain": "thermal-test", "id": i} for i in range(10)]

    # To avoid hanging the test, we'll run it in a task and cancel
    dispatch_task = asyncio.create_task(cmd.execute_bucketed_dispatch(tasks, bucket_size=5))

    await asyncio.sleep(0.1)
    assert not dispatch_task.done()  # Should be blocked by thermal stability

    dispatch_task.cancel()
    cmd.bus.close()  # SovereignSharedBus is synchronous
    cmd.bus.unlink()


@pytest.mark.asyncio
async def test_adaptive_slashing_scaling(tmp_path):
    """
    Verify adaptive slashing penalty scaling via sharded history.
    """
    from unittest.mock import patch

    # use_shm=False to use ShardedAsyncSignalBus which supports .history()
    cmd = SwarmCommander(tmp_path, use_shm=False)
    await cmd.initialize()
    bus = cmd.bus

    cen = CenturionSuperv("node-1", "test-shm")
    cen.bus = bus  # Inject ShardedAsyncSignalBus for testing

    # Mock time.perf_counter to simulate a 48ms breach (3x baseline 16ms)
    # We need two values: start and end
    with patch("time.perf_counter", side_effect=[100.0, 100.048]):
        # Trigger the breach logic
        await cen._emit_with_latency(
            event_type="test_trigger", payload={}, source="node-1", routing_key="node-1"
        )

    # Retrieve signals from the governance shard
    signals = await bus.history(event_type="governance:slashing")

    assert len(signals) >= 1
    # Find the one we just emitted
    sig = signals[0]
    penalty = sig.payload["penalty"]

    # 48ms / 16ms = 3.0 scaling
    # MINOR_DEVIATION is 0.05 (SlashingPenalty.MINOR_DEVIATION)
    # Expect approx 0.15
    assert 0.149 < penalty < 0.151

    await bus.close()
