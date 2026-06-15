#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
CORTEX-Persist Unified Benchmark Suite (P50/P95/P99)
Unifies Memory and SQL benchmarking.
"""

import argparse
import json
import os
import sqlite3
import statistics
import time
import uuid
from pathlib import Path

SCALES = [100, 500, 1_000, 5_000, 10_000]
QUERY_ITERATIONS = 200

def create_temp_db(scale: int, prefix: str) -> tuple[str, float]:
    db_path = f"/tmp/cortex_{prefix}_bench_{scale}.db"
    if os.path.exists(db_path):
        os.unlink(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.execute("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL, content TEXT NOT NULL,
            fact_type TEXT NOT NULL DEFAULT 'knowledge',
            metadata TEXT DEFAULT '{}', hash TEXT,
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
    batch = [
        (
            "default",
            "cortex-bench",
            f"Fact #{i}: {uuid.uuid4().hex[:32]}",
            "knowledge" if i % 3 != 0 else "observation",
            json.dumps({"bench": True, "idx": i}),
            f"C{(i % 5) + 1}",
            "ACTIVE",
            "HOT" if i % 4 != 3 else "WARM",
            max(0.1, 1.0 - (i / scale)),
        )
        for i in range(scale)
    ]

    conn.executemany(
        "INSERT INTO facts (tenant_id, project, content, fact_type, metadata, "
        "confidence, quadrant, storage_tier, exergy_score) VALUES (?,?,?,?,?,?,?,?,?)",
        batch,
    )
    conn.commit()
    insert_ms = (time.perf_counter() - start) * 1000
    conn.close()
    return db_path, insert_ms

def _percentiles(data: list[float]) -> dict:
    s = sorted(data)
    n = len(s)
    return {
        "p50": round(s[int(n * 0.50)], 2),
        "p95": round(s[int(n * 0.95)], 2),
        "p99": round(s[min(int(n * 0.99), n - 1)], 2),
        "mean": round(statistics.mean(data), 2),
    }

def benchmark_reads(db_path: str, scale: int, include_full_scan: bool = False) -> dict:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    results = {}

    # 1. Point lookup
    lats = []
    for _ in range(QUERY_ITERATIONS):
        tid = (hash(str(time.perf_counter())) % scale) + 1
        t0 = time.perf_counter()
        conn.execute("SELECT * FROM facts WHERE id = ?", (tid,)).fetchone()
        lats.append((time.perf_counter() - t0) * 1e6)
    results["point_lookup_us"] = _percentiles(lats)

    # 2. Filtered scan
    lats = []
    for _ in range(QUERY_ITERATIONS):
        t0 = time.perf_counter()
        conn.execute(
            "SELECT id, content FROM facts WHERE tenant_id = 'default' "
            "AND fact_type = 'knowledge' AND is_tombstoned = 0 LIMIT 50"
        ).fetchall()
        lats.append((time.perf_counter() - t0) * 1e6)
    results["filtered_scan_us"] = _percentiles(lats)

    # 3. Aggregation
    lats = []
    for _ in range(QUERY_ITERATIONS):
        t0 = time.perf_counter()
        conn.execute(
            "SELECT quadrant, storage_tier, COUNT(*) FROM facts "
            "WHERE is_tombstoned = 0 GROUP BY quadrant, storage_tier"
        ).fetchall()
        lats.append((time.perf_counter() - t0) * 1e6)
    results["aggregation_us"] = _percentiles(lats)

    # 4. Full table scan (if requested, mostly for 'memory' bench)
    if include_full_scan:
        lats = []
        for _ in range(min(QUERY_ITERATIONS, 50)):
            t0 = time.perf_counter()
            conn.execute(
                "SELECT id, content, exergy_score FROM facts "
                "WHERE is_tombstoned = 0 ORDER BY exergy_score DESC"
            ).fetchall()
            lats.append((time.perf_counter() - t0) * 1e6)
        results["full_scan_us"] = _percentiles(lats)

    # 5. Ouroboros candidate scan
    lats = []
    for _ in range(QUERY_ITERATIONS):
        t0 = time.perf_counter()
        conn.execute(
            "SELECT id, decay_half_life, exergy_score, "
            "((strftime('%s','now') - strftime('%s',created_at))/86400.0) as age "
            "FROM facts WHERE confidence != 'C5' AND is_tombstoned = 0"
        ).fetchall()
        lats.append((time.perf_counter() - t0) * 1e6)
    results["ouroboros_scan_us"] = _percentiles(lats)

    conn.close()
    return results

def run_benchmark(layer: str):
    title = "Memory Architecture" if layer == "memory" else "SQL Layer"
    print("=" * 80)
    print(f"  CORTEX-Persist {title} Benchmark — P50/P95/P99 (us)")
    print("=" * 80)

    report = {}
    for scale in SCALES:
        print(f"\n--- {scale:,} facts ---")
        db_path, ins_ms = create_temp_db(scale, layer)
        print(f"  Insert: {ins_ms:.1f}ms ({scale / (ins_ms / 1000):.0f} facts/s)")

        results = benchmark_reads(db_path, scale, include_full_scan=(layer == "memory"))
        report[scale] = {"insert_ms": round(ins_ms, 2), **results}

        print(f"  {'Query':<25} {'P50':>8} {'P95':>8} {'P99':>8} {'Mean':>8}")
        print(f"  {'─' * 65}")
        for qtype, stats in results.items():
            label = qtype.replace("_us", "")
            print(f"  {label:<25} {stats['p50']:>8.1f} {stats['p95']:>8.1f} {stats['p99']:>8.1f} {stats['mean']:>8.1f}")
        os.unlink(db_path)

    out = Path(f"/tmp/cortex_{layer}_bench.json")
    out.write_text(json.dumps(report, indent=2))
    print(f"\n{'=' * 80}")
    print(f"  Report: {out}")
    print(f"{'=' * 80}")

def main():
    parser = argparse.ArgumentParser(description="CORTEX-Persist Unified Benchmark Suite")
    parser.add_argument("--layer", choices=["memory", "sql", "all"], default="all", help="Layer to benchmark")
    args = parser.parse_args()

    layers = ["memory", "sql"] if args.layer == "all" else [args.layer]
    for layer in layers:
        run_benchmark(layer)

if __name__ == "__main__":
    main()
