# [C5-REAL] Exergy-Maximized
import gc
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))
from ultramap import UltramapSubstrate


def run_benchmark(capacity, iterations=10000):
    print(f"\n--- BENCHMARK: {capacity} AGENTS ---")

    bin_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "cortex-core", "ultramap.bin"
    )
    if os.path.exists(bin_path):
        os.remove(bin_path)

    start = time.perf_counter()
    umap = UltramapSubstrate(capacity=capacity)
    alloc_time = time.perf_counter() - start
    print(f"Allocation Time: {alloc_time:.4f}s")

    metrics = {
        "write_position": [],
        "read_position": [],
        "update_control_vector": [],
        "calculate_exergy_distance": [],
    }

    # Sequential warm-up
    for i in range(min(100, capacity)):
        umap.update_agent_position(i, 1.0, 2.0, 3.0, "TARGET", 0.5)

    for i in range(iterations):
        idx = i % capacity
        t0 = time.perf_counter()
        umap.update_agent_position(idx, i * 0.1, i * 0.2, i * 0.3, "CVE-2026", 0.9)
        t1 = time.perf_counter()
        metrics["write_position"].append(t1 - t0)

    for i in range(iterations):
        idx = i % capacity
        t0 = time.perf_counter()
        _ = umap.get_agent_state(idx)
        t1 = time.perf_counter()
        metrics["read_position"].append(t1 - t0)

    for i in range(iterations):
        idx = i % capacity
        t0 = time.perf_counter()
        umap.update_control_vector(idx, 10.0, 0.05, 0.1, 0.6)
        t1 = time.perf_counter()
        metrics["update_control_vector"].append(t1 - t0)

    for i in range(iterations):
        idx = i % capacity
        t0 = time.perf_counter()
        _ = umap.calculate_exergy_distance(idx, "TARGET_DARKPOOL_0x1")
        t1 = time.perf_counter()
        metrics["calculate_exergy_distance"].append(t1 - t0)

    umap.close()
    del umap
    gc.collect()

    for op, times in metrics.items():
        times_ms = [t * 1000 for t in times]
        p50 = statistics.median(times_ms)
        try:
            p95 = statistics.quantiles(times_ms, n=100)[94]
            p99 = statistics.quantiles(times_ms, n=100)[98]
        except AttributeError:
            times_ms.sort()
            p95 = times_ms[int(len(times_ms) * 0.95)]
            p99 = times_ms[int(len(times_ms) * 0.99)]
        ops_sec = len(times) / sum(times)

        print(f"[{op}]")
        print(f"  ops/sec : {ops_sec:.2f}")
        print(f"  p50     : {p50:.4f} ms")
        print(f"  p95     : {p95:.4f} ms")
        print(f"  p99     : {p99:.4f} ms")


if __name__ == "__main__":
    for cap in [1000, 10000, 100000]:
        run_benchmark(cap, iterations=10000)
