# [C5-REAL] Exergy-Maximized

from pathlib import Path

import pytest

from babylon60.engine.core import shared_bus as shared_bus_module
from babylon60.swarm.swarm_10k import SwarmCommander
from babylon60.extensions.signals.sharded_bus import ShardedAsyncSignalBus


@pytest.fixture(autouse=True)
def mock_keyring(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("cortex.crypto.keys.keyring", None)


@pytest.mark.asyncio
async def test_sharded_signal_bus_initialization(tmp_path: Path):
    """Test that the sharded bus initializes all 16 shards correctly."""
    bus = ShardedAsyncSignalBus(base_dir=tmp_path)
    await bus.initialize()

    assert len(bus._shards) == bus.num_shards
    for i in range(bus.num_shards):
        db_file = tmp_path / f"swarm_shard_{i:03d}.db"
        assert db_file.exists(), f"Shard {i} must exist"

    await bus.close()


@pytest.mark.asyncio
async def test_swarm_commander_hierarchy(tmp_path: Path):
    """Test L0 to L2 hierarchy generation."""
    commander = SwarmCommander(bus_path=tmp_path)
    await commander.initialize()

    # Send 500 tasks to domain 'finance'
    tasks = [{"domain": "finance", "id": i} for i in range(500)]
    async with commander.strike_mode("finance"):
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


@pytest.mark.asyncio
async def test_shared_bus_falls_back_when_shared_memory_is_unavailable(monkeypatch):
    """Use an in-process ring buffer when POSIX shared memory cannot be opened."""

    class DeniedSharedMemory:
        def __init__(self, *args, **kwargs):
            raise PermissionError("shared memory disabled")

    monkeypatch.setattr(shared_bus_module, "SharedMemory", DeniedSharedMemory)

    bus = shared_bus_module.SovereignSharedBus(name="fallback-test", create=True)

    assert bus._shm is None
    assert bus._local_buf is not None

    emitted = await bus.emit("test:event", payload={"ok": True}, source="cli")

    assert emitted is True
    polled = bus.poll(-1)
    assert len(polled) == 1
    assert polled[0][1]["payload"] == {"ok": True}

    bus.close()
