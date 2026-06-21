import pytest
import asyncio
from cortex.extensions.ouroboros_mythos.mcts_planner import MCTSPlanner

@pytest.mark.asyncio
async def test_mcts_planner_real_mode():
    planner = MCTSPlanner()
    diagnosis = {"opportunity": "inference_task"}
    
    plan = await planner.synthesize_plan(diagnosis)
    
    assert "steps" in plan
    assert plan["expected_exergy"] == 5.0

@pytest.mark.asyncio
async def test_mcts_planner_dream_mode():
    planner = MCTSPlanner(max_depth=3)
    diagnosis = {"anomaly": "high_latency"}
    
    plan = await planner.run_dream_simulation(diagnosis)
    
    assert "trajectory_hash" in plan
    assert plan["expected_exergy"] == 12.5
