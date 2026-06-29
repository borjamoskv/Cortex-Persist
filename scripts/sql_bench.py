#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
cat_id: sql-bench
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


import json
import os
import sqlite3
import statistics
import time
import uuid
from pathlib import Path

SCALES = [100, 500, 1_000, 5_000, 10_000]
QUERY_ITERATIONS = 200


def create_temp_db(scale: int) -> tuple[str, float]:
    db_path = f"/tmp/cortex_sql_bench_{scale}.db"
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
    conn.execute("CREATE INDEX idx_f_tenant ON facts(tenant_id)")
    conn.execute("CREATE INDEX idx_f_project ON facts(project)")
    conn.execute("CREATE INDEX idx_f_type ON facts(fact_type)")
    conn.execute("CREATE INDEX idx_f_tomb ON facts(is_tombstoned)")
    conn.execute("CREATE INDEX idx_f_quad ON facts(quadrant)")
    conn.execute("CREATE INDEX idx_f_tier ON facts(storage_tier)")

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


def _pct(data: list[float]) -> dict:
    s = sorted(data)
    n = len(s)
    return {
        "p50": round(s[int(n * 0.50)], 2),
        "p95": round(s[int(n * 0.95)], 2),
        "p99": round(s[min(int(n * 0.99), n - 1)], 2),
        "mean": round(statistics.mean(data), 2),
    }


def bench(db_path: str, scale: int) -> dict:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    r = {}

    # Point lookup
    lats = []
    for _ in range(QUERY_ITERATIONS):
        tid = (hash(str(time.perf_counter())) % scale) + 1
        t0 = time.perf_counter()
        conn.execute("SELECT * FROM facts WHERE id = ?", (tid,)).fetchone()
        lats.append((time.perf_counter() - t0) * 1e6)
    r["point_lookup"] = _pct(lats)

    # Filtered scan
    lats = []
    for _ in range(QUERY_ITERATIONS):
        t0 = time.perf_counter()
        conn.execute(
            "SELECT id, content FROM facts WHERE tenant_id='default' "
            "AND fact_type='knowledge' AND is_tombstoned=0 LIMIT 50"
        ).fetchall()
        lats.append((time.perf_counter() - t0) * 1e6)
    r["filtered_scan"] = _pct(lats)

    # Aggregation
    lats = []
    for _ in range(QUERY_ITERATIONS):
        t0 = time.perf_counter()
        conn.execute(
            "SELECT quadrant, storage_tier, COUNT(*) FROM facts "
            "WHERE is_tombstoned=0 GROUP BY quadrant, storage_tier"
        ).fetchall()
        lats.append((time.perf_counter() - t0) * 1e6)
    r["aggregation"] = _pct(lats)

    # Ouroboros scan
    lats = []
    for _ in range(QUERY_ITERATIONS):
        t0 = time.perf_counter()
        conn.execute(
            "SELECT id, decay_half_life, exergy_score, "
            "((strftime('%s','now') - strftime('%s',created_at))/86400.0) as age "
            "FROM facts WHERE confidence != 'C5' AND is_tombstoned = 0"
        ).fetchall()
        lats.append((time.perf_counter() - t0) * 1e6)
    r["ouroboros_scan"] = _pct(lats)

    conn.close()
    return r


def main() -> None:
    print("=" * 80)
    print("  CORTEX-Persist SQL Layer Benchmark — P50/P95/P99 (microseconds)")
    print("=" * 80)

    report = {}
    for scale in SCALES:
        print(f"\n--- {scale:,} facts ---")
        db_path, ins_ms = create_temp_db(scale)
        print(f"  Insert: {ins_ms:.1f}ms ({scale / (ins_ms / 1000):.0f} facts/s)")

        results = bench(db_path, scale)
        report[scale] = {"insert_ms": round(ins_ms, 2), **results}

        print(f"  {'Query':<20} {'P50':>8} {'P95':>8} {'P99':>8} {'Mean':>8}")
        print(f"  {'─' * 52}")
        for qtype, stats in results.items():
            print(
                f"  {qtype:<20} {stats['p50']:>8.1f} {stats['p95']:>8.1f} {stats['p99']:>8.1f} {stats['mean']:>8.1f}"
            )
        os.unlink(db_path)

    out = Path("/tmp/cortex_sql_bench.json")
    out.write_text(json.dumps(report, indent=2))
    print(f"\n{'=' * 80}")
    print(f"  Report: {out}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
