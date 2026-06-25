# [C5-REAL] Exergy-Maximized
import asyncio
import time

import pytest

from legacy_research.engine.swarm_10k import ForensicLegion, SwarmCommander
from legacy_research.forensics.forensic_strike import ForensicStrikeCommander, StrikeTarget


@pytest.mark.asyncio
async def test_strike_mode_thermal_bypass(tmp_path):
    """
    Verify that StrikeMode allows dispatching even when the system is 'Hot'.
    """
    commander = SwarmCommander(tmp_path, use_shm=False)
    await commander.initialize()

    # 1. Create a 'Hot' legion (Low exergy simulation)
    # We'll manually set a legion to high uncertainty/high children
    domain = "forensic"
    legion = await commander.get_or_create_legion(domain)
    assert isinstance(legion, ForensicLegion)
    assert legion._overclocked is True  # ForensicLegion is overclocked by default

    # 2. Simulate a scenario where standard throttling would block
    # In v7.0, wait_for_thermal_stability would block if exergy < 0.7
    # ForensicLegion should skip this check.

    start_time = time.perf_counter()

    # 3. Dispatch a massive batch (100 tasks)
    tasks = [{"domain": domain, "type": "audit"} for _ in range(100)]

    # This should NOT block because _overclocked is True
    await commander.execute_global_dispatch(tasks, parallel=True)

    end_time = time.perf_counter()
    duration = end_time - start_time

    # Verification: High-concurrency dispatch should be fast (< 1s for 100 on dev)
    assert duration < 1.0
    report = await commander.get_density_report()
    assert report["agents"] >= 100

    await commander.consolidate_and_annihilate()


@pytest.mark.asyncio
async def test_forensic_strike_orchestration(tmp_path):
    """
    Verify the ForensicStrikeCommander can deploy and report findings.
    """
    commander = SwarmCommander(tmp_path, use_shm=False)
    await commander.initialize()

    strike_cmd = ForensicStrikeCommander(commander)

    target = StrikeTarget(protocol="SSV", address="0x123", methods=["liquidate"])

    # Deploy strike
    strike_id = await strike_cmd.deploy_strike(target)
    assert "strike-SSV" in strike_id

    # Wait for density to reach 1000 (10 centurions)
    for _ in range(50):
        report = await commander.get_density_report()
        if report["agents"] >= 1000:
            break
        await asyncio.sleep(0.1)

    assert report["agents"] >= 1000
    await commander.consolidate_and_annihilate()
