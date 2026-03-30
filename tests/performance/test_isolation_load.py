import asyncio
import time
import os
import shutil
from cortex.engine.isolation import SimpleIsolationEngine

async def run_sandbox_load(concurrency=100):
    engine = SimpleIsolationEngine()
    
    # Simple python script that just prints and exits
    harness = "print('load_test_success')"
    
    print(f"[*] Starting load test with {concurrency} concurrent sandboxes...")
    start_time = time.time()
    
    tasks = []
    for i in range(concurrency):
        tasks.append(engine.execute_sandbox(harness))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.time() - start_time
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("stdout") == "load_test_success\n")
    error_count = concurrency - success_count
    
    print(f"\n[RESULTS] Load test finished in {duration:.2f}s")
    print(f"[RESULTS] Success: {success_count}/{concurrency}")
    print(f"[RESULTS] Errors: {error_count}/{concurrency}")
    
    if error_count > 0:
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                print(f"Error in sandbox {i}: {r}")
            elif isinstance(r, dict) and r.get("error"):
                print(f"Logic error in sandbox {i}: {r.get('error')}")

if __name__ == "__main__":
    asyncio.run(run_sandbox_load(100))
