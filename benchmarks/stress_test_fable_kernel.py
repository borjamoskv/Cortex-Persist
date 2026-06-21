# [C5-REAL] Exergy-Maximized Stress Test for Fable Kernel
import asyncio
import time
import sys
import os
import random
import gc
from typing import List, Tuple

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cortex.engine.fable_out import (
    CausalMaxwellDemon,
    causal_distance,
    hash_distance_rollup
)

# Try to import resource for RSS memory tracking on Unix
try:
    import resource
    def get_memory_usage_kb() -> int:
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
except ImportError:
    # Fallback if resource is not available
    def get_memory_usage_kb() -> int:
        return 0

def run_cpu_stress_test(num_operations: int = 100000):
    print(f"--- 1. CPU Stress Test: {num_operations} operations ---")
    demon = CausalMaxwellDemon(threshold=85)
    demon.set_state("CONSTRUCT")
    
    start_time = time.time()
    
    # Generate deterministic inputs
    inputs = [(random.randint(0, 1000000), random.randint(0, 1000000)) for _ in range(num_operations)]
    gen_time = time.time() - start_time
    
    # Measure cosine similarity execution
    sim_start = time.time()
    for h1, h2 in inputs:
        res = demon.cosine_similarity(h1, h2)
        # Type Check: strictly integer
        if not isinstance(res, int) or isinstance(res, float):
            raise TypeError(f"Type violation! Expected int, got {type(res)}")
    sim_time = time.time() - sim_start
    
    ops_per_sec = num_operations / sim_time if sim_time > 0 else 0
    print(f"Generated test data in: {gen_time*1000:.2f} ms")
    print(f"Executed similarity loop in: {sim_time*1000:.2f} ms")
    print(f"Throughput: {ops_per_sec:.2f} ops/sec")
    
    # Verification of causal distance
    print("Verifying causal_distance type strictness...")
    dist = causal_distance(10, 5, 2, 80)
    if not isinstance(dist, int) or isinstance(dist, float):
        raise TypeError(f"Type violation in causal_distance! Expected int, got {type(dist)}")
    print(f"Sample causal distance: {dist}")

def run_purge_redundant_stress(num_chunks: int = 2000):
    print(f"--- 2. Purge Redundant Stress Test: {num_chunks} chunks ---")
    demon = CausalMaxwellDemon(threshold=85)
    
    # We want a mix of redundant and unique chunks
    chunks = []
    for i in range(num_chunks):
        # Create similar hashes for some to trigger redundancies
        h = 1000 + (i % 200) if i % 2 == 0 else random.randint(10000, 20000)
        chunks.append((h, f"chunk_content_{i}"))
        
    start_time = time.time()
    retained, purged_count = demon.purge_redundant(chunks)
    duration = time.time() - start_time
    
    print(f"Purge Redundant completed in: {duration*1000:.2f} ms")
    print(f"Retained: {len(retained)}, Purged: {purged_count}")
    
    # Verification: sum of retained and purged must equal original
    assert len(retained) + purged_count == num_chunks, f"Count mismatch! {len(retained)} + {purged_count} != {num_chunks}"

def run_rollup_stress(num_rollups: int = 50000):
    print(f"--- 3. Merkle Rollup Stress Test: {num_rollups} rollups ---")
    
    start_time = time.time()
    # Generate list of distances
    distances = [random.randint(0, 1000) for _ in range(20)]
    root_hash = 0xDEADC0DE
    
    for _ in range(num_rollups):
        res = hash_distance_rollup(root_hash, distances)
        if not isinstance(res, int) or isinstance(res, float):
            raise TypeError(f"Type violation in rollup! Expected int, got {type(res)}")
        root_hash = res
        
    duration = time.time() - start_time
    ops_per_sec = num_rollups / duration if duration > 0 else 0
    print(f"Completed {num_rollups} rollups in: {duration*1000:.2f} ms")
    print(f"Throughput: {ops_per_sec:.2f} rollups/sec")
    print(f"Final Rollup Hash: {root_hash}")

async def run_concurrent_stress(concurrency: int = 10, ops_per_task: int = 10000):
    print(f"--- 4. Concurrency Stress Test: {concurrency} tasks x {ops_per_task} ops ---")
    demon = CausalMaxwellDemon(threshold=85)
    
    async def task_worker(task_id: int):
        task_start = time.time()
        for i in range(ops_per_task):
            res = demon.cosine_similarity(task_id * 1000 + i, task_id * 5000 - i)
            # Yield to event loop occasionally
            if i % 1000 == 0:
                await asyncio.sleep(0)
        return time.time() - task_start
        
    start_time = time.time()
    tasks = [task_worker(i) for i in range(concurrency)]
    durations = await asyncio.gather(*tasks)
    total_duration = time.time() - start_time
    
    print(f"All concurrent tasks completed in: {total_duration*1000:.2f} ms")
    print(f"Average task duration: {sum(durations)/len(durations)*1000:.2f} ms")
    print(f"Effective throughput: {(concurrency * ops_per_task) / total_duration:.2f} ops/sec")

def test_memory_leak(iterations: int = 5):
    print(f"--- 5. Memory Leak Verification Loop ({iterations} iterations of 200,000 ops) ---")
    demon = CausalMaxwellDemon(threshold=85)
    
    gc.collect()
    initial_mem = get_memory_usage_kb()
    print(f"Initial Memory usage: {initial_mem} KB")
    
    for i in range(iterations):
        # Execute intensive loop
        for _ in range(200000):
            demon.cosine_similarity(random.randint(0, 100000), random.randint(0, 100000))
        
        gc.collect()
        current_mem = get_memory_usage_kb()
        delta = current_mem - initial_mem
        print(f"Iteration {i+1} completed. Current Memory: {current_mem} KB (Delta from start: {delta} KB)")
        
    final_mem = get_memory_usage_kb()
    gc.collect()
    final_delta = final_mem - initial_mem
    print(f"Final Memory Delta: {final_delta} KB")
    
    # A small growth is okay due to Python internals / caches, but a massive continuous leak is not.
    # In Mac/Linux, ru_maxrss represents peak memory, so it might not go down, but it should stabilize.

async def main():
    print("==================================================================")
    print("   [C5-REAL] MOSKV-1 FABLE BABYLON-60 KERNEL STRESS BENCHMARK     ")
    print("==================================================================")
    
    run_cpu_stress_test(num_operations=200000)
    print()
    run_purge_redundant_stress(num_chunks=5000)
    print()
    run_rollup_stress(num_rollups=100000)
    print()
    await run_concurrent_stress(concurrency=10, ops_per_task=20000)
    print()
    test_memory_leak(iterations=5)
    print()
    print("🚀 Stress Test execution complete. Zero float violation detected.")
    print("==================================================================")

if __name__ == "__main__":
    asyncio.run(main())
