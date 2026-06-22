# [C5-REAL] Exergy-Maximized
"""
Concurrent Stress Benchmark for Evolution Ledger (Vector A).
Tests multi-threaded mutation writes to validate hash chain integrity
and sequence idempotence under heavy parallel load.
"""

import concurrent.futures
import os
import tempfile
import time
from typing import Any

from cortex.engine.checkpoint import CheckpointManager
from cortex.engine.evolution_ledger import ControlVector, EvolutionLedger


def worker_task(ledger: EvolutionLedger, agent_idx: int, mutations_per_worker: int) -> list[float]:
    latencies = []
    vector = ControlVector(1.0, 0.05, 0.1, 0.5)
    for _ in range(mutations_per_worker):
        new_vector = ControlVector(
            vector.queue_depth + 0.1, vector.error_rate, vector.causal_entropy, vector.cpu_load
        )
        ledger.record_mutation(
            agent_idx=agent_idx,
            vector_before=vector,
            vector_after=new_vector,
            source="benchmark_worker",
        )
        vector = new_vector
        latencies.append(ledger._last_write_latency_ms)
    return latencies


def run_concurrent_benchmark(workers: int = 10, mutations_per_worker: int = 1000) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "evolution_stress.jsonl")
        ledger = EvolutionLedger(log_path)

        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(worker_task, ledger, i, mutations_per_worker)
                for i in range(workers)
            ]

            latencies = []
            for f in concurrent.futures.as_completed(futures):
                latencies.extend(f.result())

        elapsed = time.perf_counter() - start_time
        total_mutations = workers * mutations_per_worker

        # Verify Integrity
        try:
            report = ledger.verify_integrity()
        except Exception as e:
            report = {"status": "CRASHED", "error": str(e)}

        # Checkpoints
        manager = CheckpointManager(ledger, chunk_size=1000)
        manager.generate_index()
        cp_report = manager.verify_ledger_with_checkpoints()

        return {
            "total_mutations": total_mutations,
            "elapsed_sec": elapsed,
            "ops_per_sec": total_mutations / elapsed,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "integrity_report": report,
            "checkpoint_report": cp_report,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("VECTOR A: Evolution Ledger Concurrency Stress Test")
    print("=" * 60)

    workers = 10
    mutations_per_worker = 1000
    print(
        f"Target: {workers} workers x {mutations_per_worker} mutations = {workers * mutations_per_worker} ops"
    )

    result = run_concurrent_benchmark(workers, mutations_per_worker)

    print("\n[ Performance ]")
    print(f"Elapsed:     {result['elapsed_sec']:.3f} s")
    print(f"Throughput:  {result['ops_per_sec']:.1f} ops/sec")
    print(f"Avg Latency: {result['avg_latency_ms']:.3f} ms/write")

    print("\n[ Ledger Integrity ]")
    print(f"Status: {result['integrity_report'].get('status')}")
    if result["integrity_report"].get("errors"):
        print(f"Errors Detected: {len(result['integrity_report']['errors'])}")
        print(f"Sample Error: {result['integrity_report']['errors'][0]}")

    print("\n[ Checkpoint Matrix ]")
    print(f"Status: {result['checkpoint_report'].get('status')}")
    print(f"Chunks Verified: {result['checkpoint_report'].get('verified_chunks')}")
