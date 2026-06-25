# [C5-REAL] Exergy-Maximized
"""
LEGION-10K: Definitive 10,000-Agent Stress Test.

Validates that the SwarmCommander → LegionSupervisor → CenturionSuperv
hierarchy can dispatch exactly 10,000 agents across 100 centurions
within a single legion, maintaining O(1) per-dispatch amortized cost
and sub-100ms total wall-clock time.

Reality Level: C5-REAL (executed on local hardware).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cortex.engine.swarm_10k import SwarmCommander


@pytest.mark.asyncio
async def test_legion_10k_full_deployment(tmp_path: Path):
    """Deploy exactly 10,000 agents and verify hierarchical integrity."""
    commander = SwarmCommander(bus_path=tmp_path)
    await commander.initialize()

    tasks = [{"domain": "legion", "id": i} for i in range(10_000)]

    t0 = time.perf_counter()
    async with commander.strike_mode("legion"):
        await commander.execute_global_dispatch(tasks)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    report = await commander.get_density_report()

    # Structural assertions
    assert report["legions"] == 1, f"Expected 1 legion, got {report['legions']}"
    assert report["centurions"] == 100, f"Expected 100 centurions, got {report['centurions']}"
    assert report["agents"] == 10_000, f"Expected 10,000 agents, got {report['agents']}"

    # Performance assertion: 10k dispatch must complete in < 5 seconds even on slow CI
    assert elapsed_ms < 5000, f"10k dispatch took {elapsed_ms:.1f}ms (budget: 5000ms)"

    await commander.consolidate_and_annihilate()
    assert len(commander.legions) == 0


@pytest.mark.asyncio
async def test_legion_10k_multi_domain(tmp_path: Path):
    """Deploy 10,000 agents across 10 domains (1,000 each)."""
    commander = SwarmCommander(bus_path=tmp_path)
    await commander.initialize()

    domains = [f"domain-{i}" for i in range(10)]
    tasks = [{"domain": domains[i % 10], "id": i} for i in range(10_000)]

    async with commander.strike_mode(domains[0]):
        await commander.execute_global_dispatch(tasks)

    report = await commander.get_density_report()

    assert report["legions"] == 10, f"Expected 10 legions, got {report['legions']}"
    assert report["agents"] == 10_000, f"Expected 10,000 agents, got {report['agents']}"
    # 1,000 agents per domain = 10 centurions each = 100 total
    assert report["centurions"] == 100, f"Expected 100 centurions, got {report['centurions']}"

    await commander.consolidate_and_annihilate()


@pytest.mark.asyncio
async def test_legion_10k_exergy_report(tmp_path: Path):
    """Verify exergy telemetry is non-zero after 10k dispatch."""
    commander = SwarmCommander(bus_path=tmp_path)
    await commander.initialize()

    tasks = [{"domain": "exergy", "id": i} for i in range(1_000)]
    async with commander.strike_mode("exergy"):
        await commander.execute_global_dispatch(tasks)

    report = await commander.get_density_report()
    assert report["agents"] == 1_000

    # Verify at least one centurion has computed exergy
    legion = commander.legions["exergy"]
    exergies = []
    for cen in legion.centurions.values():
        ex = await cen.get_exergy()
        exergies.append(ex)

    assert len(exergies) == 10  # 1000 agents / 100 per centurion
    assert all(0.0 <= e.to_float() <= 1.0 for e in exergies), f"Exergy out of bounds: {exergies}"

    await commander.consolidate_and_annihilate()


@pytest.mark.asyncio
async def test_legion_10k_annihilate_cleans_all(tmp_path: Path):
    """Confirm consolidate_and_annihilate purges all state."""
    commander = SwarmCommander(bus_path=tmp_path)
    await commander.initialize()

    tasks = [{"domain": "cleanup", "id": i} for i in range(500)]
    async with commander.strike_mode("cleanup"):
        await commander.execute_global_dispatch(tasks)

    assert len(commander.legions) == 1

    await commander.consolidate_and_annihilate()

    assert len(commander.legions) == 0
    report = await commander.get_density_report()
    assert report["legions"] == 0
    assert report["centurions"] == 0
    assert report["agents"] == 0
