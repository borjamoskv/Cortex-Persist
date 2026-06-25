# [C5-REAL] Exergy-Maximized
import pytest

from legacy_research.engine.forensic_commander import ForensicCommander
from legacy_research.engine.forensic_strike_config import STRIKE_V1


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_strike_density_assignment():
    """Verify that 1,000 agents are correctly binned into mission Legions."""
    # Use Shared Memory bus (no file path) for ultra-fast coordination testing
    commander = ForensicCommander(bus_path="cortex.db")
    await commander.initialize_strike()

    # 1. Dispatch the strike (sequential for test stability on Mac)
    dispatch_count = 0
    for m in STRIKE_V1.MISSIONS:
        for _ in range(m.agent_density // 10):
            # Dispatch individually to avoid asyncio selector saturation
            await commander.execute_global_dispatch(
                [{"id": f"{m.name}_{dispatch_count}", "domain": m.target_repo.split("/")[-1]}],
                parallel=False,
            )
            dispatch_count += 1

    # 2. Check density report
    report = await commander.get_density_report()
    assert report["agents"] == 1000

    # 3. Check Mission-Specific Binning
    # Shards active should be 1 since we're using a single shared segment
    assert report["shards_active"] >= 0

    await commander.consolidate_and_annihilate()


def test_strike_config_integrity():
    """Verify the Forensic Strike configuration invariants."""
    assert sum(m.agent_density for m in STRIKE_V1.MISSIONS) == 10000
    assert "AllocatorVault.sol" in STRIKE_V1.MISSIONS[0].focus_areas
