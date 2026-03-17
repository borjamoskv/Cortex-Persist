"""Tests for CORTEX-SWARM-10K Sharded Architecture."""

from pathlib import Path

import pytest

from cortex.engine.swarm_10k import SwarmCommander
from cortex.extensions.signals.sharded_bus import ShardedAsyncSignalBus


@pytest.mark.asyncio
async def test_sharded_signal_bus_initialization(tmp_path: Path):
    """Test that the sharded bus initializes all 16 shards correctly."""
    bus = ShardedAsyncSignalBus(base_dir=tmp_path)
    await bus.initialize()

    assert len(bus._shards) == 16
    for i in range(16):
        db_file = tmp_path / f"swarm_shard_{i:02x}.db"
        assert db_file.exists(), f"Shard {i} must exist"

    await bus.close()


@pytest.mark.asyncio
async def test_swarm_commander_hierarchy(tmp_path: Path):
    """Test L0 to L2 hierarchy generation."""
    commander = SwarmCommander(bus_path=tmp_path)
    await commander.initialize()

    # Send 500 tasks to domain 'finance'
    tasks = [{"domain": "finance", "id": i} for i in range(500)]
    await commander.execute_global_dispatch(tasks)

    report = await commander.get_density_report()
    assert report["legions"] == 1
    # 500 tasks, each agent handles 1 task.
    # 500 agents require 5 centurions (cap 100)
    assert report["centurions"] == 5
    assert report["agents"] == 500

    await commander.consolidate_and_annihilate()
    # Check teardown
    assert len(commander.legions) == 0
