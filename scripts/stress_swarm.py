import asyncio
import time
import json
import argparse
from cortex.engine.legion import SwarmInductor

async def stress_swarm(replicas=100, density=100):
    """
    Runs a real SwarmInductor cycle with non-mocked sandboxes.
    We use a very simple ARC-like task that can be solved quickly.
    """
    context = {
        "arc_task": True,
        "training_examples": [
            {"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]} # Identity
        ],
        "test_input": [[5, 6], [7, 8]]
    }
    
    # We use SwarmInductor with a real Maxwell Audit
    inductor = SwarmInductor(replica_count=replicas)
    
    print(f"[*] Starting Swarm Stress Test with {replicas} replicas (Density: {density})...")
    start_time = time.time()
    
    # We call induce. Inside legion.py, it will spawn 'replicas' agents (though mocked mostly for now, 
    # but the Maxwell Audit WILL run the sandboxes).
    # Wait, in legion.py:203, if arc_task is True, it uses ARCAgent. 
    # To avoid calling expensive LLMs, we'll patch the agent but keep the AUDIT (sandboxes) real.
    
    from unittest.mock import AsyncMock, patch
    with patch("cortex.agents.arc_agi_3.agent.ARCAgent.run", new_callable=AsyncMock) as mock_agent:
        # Mock agent returns a few candidates (PeARL code)
        # We'll make it return a candidate that passes the audit.
        mock_agent.return_value = "def transform(grid):\n    return grid"
        
        result = await inductor.induce("stress_arc_identity", context, density=density)
        
    duration = time.time() - start_time
    
    print(f"\n[RESULTS] Swarm Stress Test finished in {duration:.2f}s")
    print(f"[RESULTS] Success: {result.success}")
    if not result.success:
        print(f"[RESULTS] Error: {result.error}")
    else:
        print(f"[RESULTS] Solution: {result.code[:50]}...")
        print(f"[RESULTS] Exergy: {result.exergy:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicas", type=int, default=100)
    parser.add_argument("--density", type=int, default=100)
    args = parser.parse_args()
    
    asyncio.run(stress_swarm(args.replicas, args.density))
