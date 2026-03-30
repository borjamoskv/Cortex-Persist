import asyncio
import json
import os
import sys
import time
from typing import Any
from cortex.agents.arc_agi_3.agent import ARCAgent
from cortex.engine.legion import SwarmInductor

# Benchmark tasks (curated subset)
BENCHMARK_TASKS = [
    {
        "id": "3c9ad87c",
        "name": "Object Recolor (Symmetry)",
        "train": [
            {"input": [[0,0,0,0,0],[0,1,1,1,0],[0,1,1,1,0],[0,1,1,1,0],[0,0,0,0,0]], "output": [[0,0,0,0,0],[0,2,2,2,0],[0,2,2,2,0],[0,2,2,2,0],[0,0,0,0,0]]},
            {"input": [[0,0,0],[0,1,0],[0,0,0]], "output": [[0,0,0],[0,2,0],[0,0,0]]}
        ],
        "test": [{"input": [[1,1],[1,1]], "output": [[2,2],[2,2]]}]
    },
    {
        "id": "6150a2bd",
        "name": "Rotation 90",
        "train": [
            {"input": [[1,0,0],[0,1,0],[0,0,1]], "output": [[0,0,1],[0,1,0],[1,0,0]]},
            {"input": [[1,1],[0,0]], "output": [[0,1],[0,1]]}
        ],
        "test": [{"input": [[5,0],[5,0]], "output": [[0,0],[5,5]]}]
    }
]

async def run_benchmark():
    print("🚀 ARC-AGI-3 Sovereign Benchmark (Ω-Swarm-100)")
    print("-" * 50)
    
    # Force Swarm-100 mode
    os.environ["ARC_STRESS_TEST"] = "true"
    
    agent = ARCAgent()
    
    results = []
    
    for task in BENCHMARK_TASKS:
        print(f"\nTask: {task['name']} ({task['id']})")
        start_time = time.time()
        
        try:
            # We want to use the agent.run which calls SwarmInductor if ARC_STRESS_TEST=true
            # Wait, ARCAgent.run takes (task_data). 
            # It then calls synthesize_and_execute which calls search_engine.search.
            # search_engine.search calls inductor.induce_candidates.
            # inductor.induce_candidates calls SwarmInductor.induce if n >= 50 or is_stress_test.
            
            # For 100-agent swarm, we just need to pass n=100 or rely on env var.
            output_grid = await agent.run(task)
            
            duration = time.time() - start_time
            expected = task["test"][0]["output"]
            success = output_grid == expected
            
            print(f"  Result: {'✅ SUCCESS' if success else '❌ FAILURE'}")
            print(f"  Time: {duration:.2f}s")
            
            results.append({
                "id": task["id"],
                "success": success,
                "duration": duration
            })
            
        except Exception as e:
            print(f"  🔥 CRASH: {e}")
            results.append({
                "id": task["id"],
                "success": False,
                "error": str(e)
            })

    print("-" * 50)
    total_tasks = len(results)
    successful_tasks = sum(1 for r in results if r["success"])
    print(f"Summary: {successful_tasks}/{total_tasks} passed.")
    print(f"Accuracy: {(successful_tasks/total_tasks)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
