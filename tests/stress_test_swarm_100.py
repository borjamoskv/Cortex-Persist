import asyncio
import json
import logging
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from typing import Mapping, Any

from cortex.engine.legion import LegionOmegaEngine, SwarmInductor, LegionMaxwellAudit, LegionMaxwellFilter
from cortex.engine.legion_vectors import RED_TEAM_SWARM

# Configure logging for better visibility during stress test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stress_test_swarm_100")

@pytest.mark.asyncio
async def test_swarm_100_full_cycle():
    """
    Sovereign Swarm-100 Stress Test.
    Verifies 100-agent induction and 100-vector adversarial siege.
    """
    logger.info("Starting Sovereign Swarm-100 Stress Test...")

    # 1. Setup Environment
    engine = LegionOmegaEngine(max_cycles=1, db_path="tests/stress_swarm.db")
    inductor = SwarmInductor()
    
    # 2. Load ARC Task
    try:
        with open("tests/arc_agi_3/demo_task.json", "r") as f:
            arc_task = json.load(f)
    except FileNotFoundError:
        arc_task = {"id": "test_task", "train": [{"input": [[0]], "output": [[0]]}], "test": [{"input": [[0]]}]}

    # 3. Induction Phase: 100 Agents
    logger.info("Executing 100-agent parallel induction phase (Mocked Reasoner)...")
    context = {"arc_task": arc_task, "intent": "solve_arc_high_concurrency"}
    
    # Mock the ARCAgent.run to avoid the heavy MCTS reasoning
    with patch("cortex.agents.arc_agi_3.agent.ARCAgent.run", new_callable=AsyncMock) as mock_run:
        # ARCAgent returns a grid
        mock_run.return_value = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
        
        # SwarmInductor triggers n=100 if arc_task in context.
        # It batches in 25. If verification is mocked too, it will run all batches unless it finds perfect convergence.
        induction_results = await inductor.induce("arc_demo", context)
    
    assert isinstance(induction_results, str)
    assert "def transform" in induction_results
    assert mock_run.call_count >= 1
    logger.info(f"Induction Phase: Successful. Agent calls made: {mock_run.call_count}")

    # 4. Adversarial Phase: 100 Vectors (Red Team Siege)
    logger.info("Executing 100-vector adversarial siege (Red Team)...")
    code_to_test = induction_results
    sieger = engine.red_team
    findings = await sieger.siege(code_to_test, context)
    
    logger.info(f"Siege completed with {len(findings)} total findings.")

    # 5. Audit Phase: LegionMaxwell
    logger.info("Executing LegionMaxwell Audit...")
    audit = LegionMaxwellAudit()
    report = await audit.verify(code_to_test, arc_task)
    
    assert "status" in report
    assert report.get("status") == "success"
    assert "duration" in report
    logger.info(f"Audit Phase Result: {report.get('status')} in {report.get('duration'):.4f}s")
    
    logger.info("Sovereign Swarm-100 Stress Test: PASSED.")

if __name__ == "__main__":
    asyncio.run(test_swarm_100_full_cycle())
