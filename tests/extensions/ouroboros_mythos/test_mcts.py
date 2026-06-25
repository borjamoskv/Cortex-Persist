import pytest
import struct
import hashlib
from legacy_research.extensions.ouroboros_mythos.mcts_planner import MCTSPlanner

@pytest.mark.asyncio
async def test_mcts_planner_real_mode():
    planner = MCTSPlanner()
    diagnosis = {"cpu_pct_scaled": 5000, "ram_pct_scaled": 5000, "latency_ms": 45}
    
    plan = await planner.synthesize_plan(diagnosis)
    
    assert "steps" in plan
    assert len(plan["steps"]) == 1
    assert plan["steps"][0] == b"flush_cache"
    assert plan["expected_exergy_units"] == 7092

@pytest.mark.asyncio
async def test_mcts_planner_dream_mode():
    planner = MCTSPlanner(max_depth=3)
    diagnosis = {"cpu_pct_scaled": 5000, "ram_pct_scaled": 5000, "latency_ms": 45}
    
    plan = await planner.run_dream_simulation(diagnosis)
    
    assert "trajectory_hash" in plan
    assert len(plan["steps"]) == 3
    assert plan["expected_exergy_units"] > 0
    
    # Assert structural endianness (trajectory hash is 4 bytes representation)
    assert len(plan["trajectory_hash"]) == 4
