"""CORTEX Benchmarks — Search latency & throughput.

Measures:
  - Single search latency (p50, p95, p99)
  - Bulk insert throughput (facts/sec)
  - Concurrent search throughput (queries/sec)

Usage:
    cd cortex
    .venv/bin/python benchmarks/bench_search.py
"""

import os
import statistics
import sys
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex.engine import CortexEngine


def bench_insert(engine: CortexEngine, n: int = 500) -> float:
    """Benchmark bulk insert throughput."""
    facts = [
        f"Benchmark fact #{i}: The sovereign memory engine processes "
        f"information at velocity level {i % 10} with entropy score {i * 0.01:.2f}"
        for i in range(n)
    ]
    start = time.perf_counter()
    for fact in facts:
        engine.store(content=fact, fact_type="knowledge", project="benchmark")
    elapsed = time.perf_counter() - start
    return n / elapsed  # facts/sec


def bench_search_latency(engine: CortexEngine, queries: list[str], runs: int = 50) -> dict:
    """Benchmark search latency distribution."""
    latencies = []
    for _ in range(runs):
        for q in queries:
            start = time.perf_counter()
            engine.search(query=q, top_k=10)
            latencies.append((time.perf_counter() - start) * 1000)  # ms

    latencies.sort()
    return {
        "p50_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(latencies[int(len(latencies) * 0.95)], 2),
        "p99_ms": round(latencies[int(len(latencies) * 0.99)], 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "total_queries": len(latencies),
    }


def main():
    print("=" * 60)
    print("  CORTEX BENCHMARK — Sovereign Performance Report")
    print("=" * 60)
    print()

    db_path = "/tmp/cortex_bench.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    engine = CortexEngine(db_path=db_path)

    # Insert benchmark
    print("📦 Benchmarking insert throughput (500 facts)...")
    throughput = bench_insert(engine, n=500)
    print(f"   Throughput: {throughput:.0f} facts/sec")
    print()

    # Search benchmark
    queries = [
        "sovereign memory engine",
        "entropy score processing",
        "velocity level information",
        "benchmark performance",
        "knowledge facts data",
    ]
    print(f"🔎 Benchmarking search latency ({len(queries)} queries × 50 runs)...")
    results = bench_search_latency(engine, queries)
    print(f"   p50:  {results['p50_ms']:.1f} ms")
    print(f"   p95:  {results['p95_ms']:.1f} ms")
    print(f"   p99:  {results['p99_ms']:.1f} ms")
    print(f"   mean: {results['mean_ms']:.1f} ms")
    print(f"   Total queries: {results['total_queries']}")
    print()

    # QPS
    total_time = results['mean_ms'] * results['total_queries'] / 1000
    qps = results['total_queries'] / total_time if total_time > 0 else 0
    print(f"⚡ Estimated QPS: {qps:.0f} queries/sec")
    print()
    print("=" * 60)

    # Cleanup
    os.remove(db_path)


if __name__ == "__main__":
    main()
