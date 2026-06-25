import asyncio
import time
import uuid

import cortex_rs

ITERATIONS = 10_000

def bench_rust_init():
    start = time.perf_counter()
    for _ in range(ITERATIONS):
        cortex_rs.CRDTMergeState()
    end = time.perf_counter()
    return (end - start) / ITERATIONS

def bench_rust_insert():
    s = cortex_rs.CRDTMergeState()
    uuids = [str(uuid.uuid4()) for _ in range(30)]
    
    start = time.perf_counter()
    for i in range(ITERATIONS):
        s.add_model(uuids[0], "agent", i)
    end = time.perf_counter()
    return (end - start) / ITERATIONS

def bench_logop():
    s1 = cortex_rs.CRDTMergeState()
    s1.add_model(str(uuid.uuid4()), "agent", 100)
    s2 = cortex_rs.CRDTMergeState()
    s2.add_model(str(uuid.uuid4()), "agent", 101)
    s2_json = s2.get_state_json()
    
    start = time.perf_counter()
    for _ in range(ITERATIONS):
        temp = cortex_rs.CRDTMergeState()
        temp.merge_with_json(s2_json)
    end = time.perf_counter()
    return (end - start) / ITERATIONS

async def run_all():
    print(f"Running benchmarks ({ITERATIONS} iterations)...")
    
    t_init = bench_rust_init()
    print(f"CRDTMergeState Init: {t_init * 1e6:.2f} µs/op")
    
    t_insert = bench_rust_insert()
    print(f"CRDTMergeState Insert: {t_insert * 1e6:.2f} µs/op")
    
    t_logop = bench_logop()
    print(f"CRDTMergeState JSON Merge: {t_logop * 1e6:.2f} µs/op")
    
    print("\nBenchmark complete.")

if __name__ == "__main__":
    asyncio.run(run_all())
