#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Memory Architecture Benchmark (P50/P95/P99)

Red Team demanded evidence: "Prove the Tripartite Memory scales."
This script generates synthetic facts, benchmarks read/write latency
at increasing scales, and reports P50/P95/P99 percentiles.

Output: JSON report + human-readable table.
"""

import json
import os
import sqlite3
import statistics
import time
import uuid
from pathlib import Path

# Scales to benchmark
SCALES = [100, 500, 1_000, 5_000, 10_000]
QUERY_ITERATIONS = 200


def create_temp_db(scale: int) -> tuple[str, float]:
    """Create a temporary DB with `scale` facts. Returns (path, insert_time_ms)."""
    db_path = f"/tmp/cortex_bench_{scale}.db"
    if os.path.exists(db_path):
        os.unlink(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.execute("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            fact_type TEXT NOT NULL DEFAULT 'knowledge',
            metadata TEXT DEFAULT '{}',
            hash TEXT,
            confidence TEXT DEFAULT 'C3',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_tombstoned INTEGER NOT NULL DEFAULT 0,
            quadrant TEXT NOT NULL DEFAULT 'ACTIVE',
            storage_tier TEXT NOT NULL DEFAULT 'HOT',
            exergy_score REAL NOT NULL DEFAULT 1.0,
            category TEXT NOT NULL DEFAULT 'general',
            parent_id INTEGER,
            decay_half_life REAL DEFAULT 30.0,
            tags TEXT DEFAULT '[]'
        )
    """)
    conn.execute("CREATE INDEX idx_facts_tenant ON facts(tenant_id)")
    conn.execute("CREATE INDEX idx_facts_project ON facts(project)")
    conn.execute("CREATE INDEX idx_facts_type ON facts(fact_type)")
    conn.execute("CREATE INDEX idx_facts_tombstone ON facts(is_tombstoned)")
    conn.execute("CREATE INDEX idx_facts_quadrant ON facts(quadrant)")
    conn.execute("CREATE INDEX idx_facts_tier ON facts(storage_tier)")

    start = time.perf_counter()
    batch = []
    for i in range(scale):
        batch.append(
            (
                "default",
                "cortex-bench",
                f"Benchmark fact #{i}: {uuid.uuid4().hex[:32]}",
                "knowledge" if i % 3 != 0 else "observation",
                json.dumps({"bench": True, "idx": i}),
                f"C{(i % 5) + 1}",
                "ACTIVE",
                "HOT" if i % 4 != 3 else "WARM",
                max(0.1, 1.0 - (i / scale)),
            )
        )

    conn.executemany(
        "INSERT INTO facts (tenant_id, project, content, fact_type, metadata, "
        "confidence, quadrant, storage_tier, exergy_score) VALUES (?,?,?,?,?,?,?,?,?)",
        batch,
    )
    conn.commit()
    insert_ms = (time.perf_counter() - start) * 1000
    conn.close()
    return db_path, insert_ms


def benchmark_reads(db_path: str, scale: int) -> dict:
    """Benchmark various read patterns and return latency percentiles."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row

    results = {}

    # 1. Point lookup by ID
    latencies = []
    for _ in range(QUERY_ITERATIONS):
        target_id = (hash(str(time.perf_counter())) % scale) + 1
        start = time.perf_counter()
        conn.execute("SELECT * FROM facts WHERE id = ?", (target_id,)).fetchone()
        latencies.append((time.perf_counter() - start) * 1_000_000)
    results["point_lookup_us"] = _percentiles(latencies)

    # 2. Filtered scan (tenant + type)
    latencies = []
    for _ in range(QUERY_ITERATIONS):
        start = time.perf_counter()
        conn.execute(
            "SELECT id, content FROM facts WHERE tenant_id = 'default' "
            "AND fact_type = 'knowledge' AND is_tombstoned = 0 LIMIT 50"
        ).fetchall()
        latencies.append((time.perf_counter() - start) * 1_000_000)
    results["filtered_scan_us"] = _percentiles(latencies)

    # 3. Aggregation (COUNT + GROUP BY)
    latencies = []
    for _ in range(QUERY_ITERATIONS):
        start = time.perf_counter()
        conn.execute(
            "SELECT quadrant, storage_tier, COUNT(*) FROM facts "
            "WHERE is_tombstoned = 0 GROUP BY quadrant, storage_tier"
        ).fetchall()
        latencies.append((time.perf_counter() - start) * 1_000_000)
    results["aggregation_us"] = _percentiles(latencies)

    # 4. Full table scan (worst case)
    latencies = []
    for _ in range(min(QUERY_ITERATIONS, 50)):
        start = time.perf_counter()
        conn.execute(
            "SELECT id, content, exergy_score FROM facts "
            "WHERE is_tombstoned = 0 ORDER BY exergy_score DESC"
        ).fetchall()
        latencies.append((time.perf_counter() - start) * 1_000_000)
    results["full_scan_us"] = _percentiles(latencies)

    # 5. Ouroboros candidate scan (the real hot path)
    latencies = []
    for _ in range(QUERY_ITERATIONS):
        start = time.perf_counter()
        conn.execute(
            "SELECT id, content, created_at, decay_half_life, exergy_score, "
            "((strftime('%s', 'now') - strftime('%s', created_at)) / 86400.0) as age_days "
            "FROM facts WHERE confidence != 'C5' AND is_tombstoned = 0"
        ).fetchall()
        latencies.append((time.perf_counter() - start) * 1_000_000)
    results["ouroboros_scan_us"] = _percentiles(latencies)

    conn.close()
    return results


def _percentiles(data: list[float]) -> dict:
    """Compute P50, P95, P99 from a list of latencies."""
    data_sorted = sorted(data)
    n = len(data_sorted)
    return {
        "p50": round(data_sorted[int(n * 0.50)], 2),
        "p95": round(data_sorted[int(n * 0.95)], 2),
        "p99": round(data_sorted[min(int(n * 0.99), n - 1)], 2),
        "mean": round(statistics.mean(data), 2),
        "stdev": round(statistics.stdev(data), 2) if len(data) > 1 else 0.0,
    }


def main() -> None:
    print("=" * 78)
    print("  CORTEX-Persist Memory Architecture Benchmark")
    print("  Red Team Evidence: P50 / P95 / P99 Latency Proof")
    print("=" * 78)

    all_results = {}

    for scale in SCALES:
        print(f"\n{'─' * 78}")
        print(f"  Scale: {scale:,} facts")
        print(f"{'─' * 78}")

        db_path, insert_ms = create_temp_db(scale)
        print(
            f"  Insert {scale:,} facts: {insert_ms:.1f}ms ({scale / (insert_ms / 1000):.0f} facts/s)"
        )

        results = benchmark_reads(db_path, scale)
        all_results[scale] = {"insert_ms": round(insert_ms, 2), "reads": results}

        print(
            f"\n  {'Query Type':<25} {'P50 (us)':>10} {'P95 (us)':>10} {'P99 (us)':>10} {'Mean':>10}"
        )
        print(f"  {'─' * 65}")
        for query_type, stats in results.items():
            label = query_type.replace("_us", "")
            print(
                f"  {label:<25} {stats['p50']:>10.1f} {stats['p95']:>10.1f} "
                f"{stats['p99']:>10.1f} {stats['mean']:>10.1f}"
            )

        os.unlink(db_path)

    report_path = Path("/tmp/cortex_memory_bench.json")
    report_path.write_text(json.dumps(all_results, indent=2))
    print(f"\n{'=' * 78}")
    print(f"  Full report saved to: {report_path}")
    print(f"{'=' * 78}")


if __name__ == "__main__":
    main()
