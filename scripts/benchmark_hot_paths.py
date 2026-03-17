"""
scripts/benchmark_hot_paths.py

Benchmark the three hot paths in the CORTEX storage engine:
  1. Dedup lookup (exact-hash match on active facts)
  2. FTS search (full-text search via facts_fts)
  3. Vector ANN lookup (nearest neighbor via fact_embeddings / sqlite-vec)

Emits latency percentiles (p50, p95, p99) and appends results
to artifacts/health/system_integrity_report.json.

Usage:
    python scripts/benchmark_hot_paths.py [--db PATH] [--iterations N] [--out PATH]

Thresholds (from INVARIANTS.md):
    dedup   p95 < 10ms
    fts     p95 < 15ms
    vector  p95 < 20ms  (skipped if sqlite-vec not available)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sqlite3
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("cortex.benchmark")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = os.environ.get("CORTEX_DB_PATH", str(REPO_ROOT / "cortex.db"))
DEFAULT_OUT = REPO_ROOT / "artifacts" / "health" / "system_integrity_report.json"

# Latency thresholds in milliseconds (from INVARIANTS.md INV-012..014)
THRESHOLDS_MS = {
    "dedup_p95": 10.0,
    "fts_p95": 15.0,
    "vector_p95": 20.0,
}


def _percentile(samples: list[float], p: float) -> float:
    if not samples:
        return 0.0
    sorted_s = sorted(samples)
    k = (p / 100) * (len(sorted_s) - 1)
    lo, hi = int(k), min(int(k) + 1, len(sorted_s) - 1)
    return sorted_s[lo] + (k - lo) * (sorted_s[hi] - sorted_s[lo])


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return bool(row and row[0])


# ─── Benchmark: Dedup (exact hash lookup) ────────────────────────────────────


def bench_dedup(conn: sqlite3.Connection, iterations: int) -> dict:
    """Exact-hash lookup on active, non-tombstoned facts (dedup hot path)."""
    rows = conn.execute(
        "SELECT hash FROM facts WHERE hash IS NOT NULL AND is_tombstoned=0 AND is_quarantined=0 LIMIT 500"
    ).fetchall()
    if not rows:
        return {"status": "skip", "reason": "no hashed facts to sample"}
    hashes = [r[0] for r in rows]

    samples: list[float] = []
    for _ in range(iterations):
        h = random.choice(hashes)
        t0 = time.perf_counter()
        conn.execute(
            "SELECT id FROM facts WHERE hash=? AND is_tombstoned=0 AND is_quarantined=0 LIMIT 1",
            (h,),
        ).fetchone()
        samples.append((time.perf_counter() - t0) * 1000)

    p50 = _percentile(samples, 50)
    p95 = _percentile(samples, 95)
    p99 = _percentile(samples, 99)
    status = "PASS" if p95 < THRESHOLDS_MS["dedup_p95"] else "FAIL"
    return {
        "status": status,
        "iterations": iterations,
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "p99_ms": round(p99, 3),
        "threshold_p95_ms": THRESHOLDS_MS["dedup_p95"],
    }


# ─── Benchmark: FTS search ───────────────────────────────────────────────────


def bench_fts(conn: sqlite3.Connection, iterations: int) -> dict:
    """FTS5 keyword search via facts_fts virtual table."""
    if not _table_exists(conn, "facts_fts"):
        return {"status": "skip", "reason": "facts_fts not enabled"}

    # Pull a sample of distinct words from the content column for realistic queries
    rows = conn.execute(
        "SELECT content FROM facts WHERE is_tombstoned=0 AND is_quarantined=0 LIMIT 200"
    ).fetchall()
    if not rows:
        return {"status": "skip", "reason": "no searchable facts"}

    # Extract tokens: take first word of each row as a realistic FTS probe
    tokens = list({r[0].split()[0] for r in rows if r[0] and r[0].strip()})[:100] or ["cortex"]

    samples: list[float] = []
    for _ in range(iterations):
        term = random.choice(tokens)
        t0 = time.perf_counter()
        conn.execute(
            "SELECT rowid FROM facts_fts WHERE facts_fts MATCH ? LIMIT 10", (term,)
        ).fetchall()
        samples.append((time.perf_counter() - t0) * 1000)

    p50 = _percentile(samples, 50)
    p95 = _percentile(samples, 95)
    p99 = _percentile(samples, 99)
    status = "PASS" if p95 < THRESHOLDS_MS["fts_p95"] else "FAIL"
    return {
        "status": status,
        "iterations": iterations,
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "p99_ms": round(p99, 3),
        "threshold_p95_ms": THRESHOLDS_MS["fts_p95"],
    }


# ─── Benchmark: Vector ANN ───────────────────────────────────────────────────


def bench_vector(conn: sqlite3.Connection, iterations: int) -> dict:
    """ANN lookup via sqlite-vec fact_embeddings table."""
    if not _table_exists(conn, "fact_embeddings"):
        return {"status": "skip", "reason": "fact_embeddings (sqlite-vec) not enabled"}

    try:
        import sqlite_vec  # type: ignore

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except (ImportError, sqlite3.OperationalError):
        return {"status": "skip", "reason": "sqlite_vec extension not loadable"}

    # Fetch one real embedding as a query vector
    row = conn.execute("SELECT embedding FROM fact_embeddings LIMIT 1").fetchone()
    if row is None:
        return {"status": "skip", "reason": "no embeddings to probe"}

    query_embedding = row[0]
    samples: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        conn.execute(
            "SELECT fact_id, distance FROM fact_embeddings WHERE embedding MATCH ? ORDER BY distance LIMIT 5",
            (query_embedding,),
        ).fetchall()
        samples.append((time.perf_counter() - t0) * 1000)

    p50 = _percentile(samples, 50)
    p95 = _percentile(samples, 95)
    p99 = _percentile(samples, 99)
    status = "PASS" if p95 < THRESHOLDS_MS["vector_p95"] else "FAIL"
    return {
        "status": status,
        "iterations": iterations,
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "p99_ms": round(p99, 3),
        "threshold_p95_ms": THRESHOLDS_MS["vector_p95"],
    }


# ─── Output ───────────────────────────────────────────────────────────────────


def _merge_report(out_path: Path, benchmarks: dict) -> None:
    """Merge benchmark results into the existing health report JSON, or create it."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
        except json.JSONDecodeError:
            pass
    existing["benchmarks"] = benchmarks
    existing["benchmark_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out_path.write_text(json.dumps(existing, indent=2))
    log.info("Benchmarks merged → %s", out_path)


def _print_results(benchmarks: dict) -> None:
    print("\n" + "─" * 55)
    print("  CORTEX Hot-Path Benchmarks")
    print("─" * 55)
    for name, result in benchmarks.items():
        status = result.get("status", "?")
        icon = {"PASS": "✅", "FAIL": "❌", "skip": "⚠️ "}.get(status, "?")
        if status == "skip":
            print(f"  {icon}  [{name}]  SKIP — {result.get('reason', '')}")
        else:
            p95 = result.get("p95_ms", "?")
            thr = result.get("threshold_p95_ms", "?")
            print(
                f"  {icon}  [{name}]  p50={result.get('p50_ms')}ms  p95={p95}ms  p99={result.get('p99_ms')}ms  (threshold p95 < {thr}ms)"
            )
    print("─" * 55 + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CORTEX hot-path benchmark")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    if not Path(args.db).exists():
        log.error("Database not found: %s", args.db)
        return 1

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-65536")

    benchmarks = {
        "dedup": bench_dedup(conn, args.iterations),
        "fts_search": bench_fts(conn, args.iterations),
        "vector_ann": bench_vector(conn, args.iterations),
    }
    conn.close()

    _print_results(benchmarks)
    _merge_report(Path(args.out), benchmarks)

    failed = [k for k, v in benchmarks.items() if v.get("status") == "FAIL"]
    if failed:
        log.error("Benchmarks FAILED: %s", failed)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
