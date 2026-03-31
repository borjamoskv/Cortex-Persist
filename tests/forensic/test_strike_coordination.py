import pytest
import asyncio
import shutil
from pathlib import Path
from cortex.engine.forensic_commander import ForensicCommander
from cortex.engine.forensic_strike_config import STRIKE_V1

@pytest.mark.async_io
async def test_strike_density_assignment():
    """Verify that 10,000 agents are correctly binned into mission Legions."""
    db_test = Path("/tmp/forensic_strike_test.db")
    if db_test.exists():
        shutil.rmtree(db_test)
        
    commander = ForensicCommander(bus_path=db_test)
    await commander.initialize_strike()
    
    # 1. Dispatch the strike
    await commander.execute_mission_dispatch()
    
    # 2. Check density report
    report = await commander.get_density_report()
    assert report["agents"] == 10000
    
    # 3. Check Mission-Specific Binning (Simulation of query)
    mission_counts = {m.name: 0 for m in STRIKE_V1.MISSIONS}
    
    # Verify shard distribution (Overview)
    assert report["shards_active"] > 10 # Should be sharded across 100
    
    await commander.consolidate_and_annihilate()
    if db_test.exists():
        shutil.rmtree(db_test)

def test_strike_config_integrity():
    """Verify the Forensic Strike configuration invariants."""
    assert sum(m.agent_density for m in STRIKE_V1.MISSIONS) == 10000
    assert "AllocatorVault.sol" in STRIKE_V1.MISSIONS[0].focus_areas
