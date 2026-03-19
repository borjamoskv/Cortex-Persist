#!/usr/bin/env python3
"""CORTEX Memory Microbenchmark — Sovereign Performance Validation.

Measures recall_secure latency and Python callback invocation
count under OLD (full-scan scoring) vs NEW (KNN MATCH pre-selection).

Usage:
    python3 scripts/memory_microbenchmark.py
"""
from __future__ import annotations

import sqlite3
import time
import uuid

import numpy as np

CORPUS_SIZES = [100, 1_000, 5_000]
QUERY_RUNS = 10
EMBEDDING_DIM = 384
LIMIT = 5
KNN_POOL = 50  # max(limit*10, 50)

_exergy_calls = 0
_decay_calls = 0


def fake_exergy(content: str) -> float:
    global _exergy_calls
    _exergy_calls += 1
    return 0.8


def fake_decay(
    is_diamond: int, timestamp: float, current_time: float, half_life: float
) -> float:
    global _decay_calls
    _decay_calls += 1
    if is_diamond:
        return 1.0
    age = max(0.0, current_time - timestamp)
    return float(0.5 ** (age / half_life))


def _setup_db(n: int) -> tuple[sqlite3.Connection, bytes]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except (ImportError, AttributeError, sqlite3.OperationalError):
        print("sqlite-vec not available — benchmark requires it.")
        raise SystemExit(1) from None

    conn.create_function("cortex_exergy", 1, fake_exergy)
    conn.create_function("cortex_decay", 4, fake_decay)

    conn.execute("""
        CREATE TABLE facts_meta (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            content TEXT,
            timestamp REAL,
            is_diamond INTEGER DEFAULT 0,
            is_bridge INTEGER DEFAULT 0,
            confidence TEXT DEFAULT '0.8',
            success_rate REAL DEFAULT 0.9,
            cognitive_layer TEXT DEFAULT 'semantic',
            parent_decision_id TEXT,
            metadata TEXT DEFAULT '{}'
        )
    """)
    conn.execute(f"""
        CREATE VIRTUAL TABLE vec_facts USING vec0(
            embedding float[{EMBEDDING_DIM}]
        )
    """)
    conn.execute(
        "CREATE INDEX idx_tenant_proj ON facts_meta(tenant_id, project_id)"
    )

    rng = np.random.default_rng(42)
    now = time.time()
    for i in range(n):
        fid = str(uuid.uuid4())
        emb = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
        emb /= np.linalg.norm(emb)
        conn.execute(
            "INSERT INTO facts_meta "
            "(id, tenant_id, project_id, content, timestamp, success_rate) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (fid, "bench", "bench", f"fact_{i}", now - i * 60, 0.9),
        )
        rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO vec_facts(rowid, embedding) VALUES (?, ?)",
            (rowid, emb.tobytes()),
        )
    conn.commit()

    q_emb = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
    q_emb /= np.linalg.norm(q_emb)
    return conn, q_emb.tobytes()


def _bench_old(conn, q_bytes, limit):
    """OLD: full-scan join + Python callbacks on every row."""
    global _exergy_calls, _decay_calls
    _exergy_calls = 0
    _decay_calls = 0
    now = time.time()
    hl = 7 * 86400

    sql = """
        SELECT *, ((1.0 - vec_distance_cosine(v.embedding, ?) / 2.0) *
             cortex_decay(m.is_diamond, m.timestamp, ?, ?) *
             m.success_rate *
             cortex_exergy(m.content)) as final_score
        FROM facts_meta m
        JOIN vec_facts v ON m.rowid = v.rowid
        WHERE m.tenant_id = ? AND m.project_id = ?
        ORDER BY final_score DESC LIMIT ?
    """

    start = time.perf_counter()
    for _ in range(QUERY_RUNS):
        conn.execute(sql, (q_bytes, now, hl, "bench", "bench", limit)).fetchall()
    elapsed = (time.perf_counter() - start) / QUERY_RUNS * 1000
    return elapsed, _exergy_calls // QUERY_RUNS, _decay_calls // QUERY_RUNS


def _bench_new(conn, q_bytes, limit, pool):
    """NEW: KNN MATCH pre-selection → Python callbacks on K only."""
    global _exergy_calls, _decay_calls
    _exergy_calls = 0
    _decay_calls = 0
    now = time.time()
    hl = 7 * 86400

    sql = """
        SELECT
            m.rowid, m.id, m.tenant_id, m.project_id,
            m.content, m.timestamp,
            m.is_diamond, m.is_bridge, m.confidence,
            m.success_rate,
            m.cognitive_layer, m.parent_decision_id,
            m.metadata, v.embedding, v.distance,
            (1.0 - v.distance / 2.0) as base_similarity,
            ((1.0 - v.distance / 2.0) *
             cortex_decay(m.is_diamond, m.timestamp, ?, ?) *
             m.success_rate *
             cortex_exergy(m.content)) as final_score
        FROM vec_facts v
        JOIN facts_meta m ON m.rowid = v.rowid
        WHERE v.embedding MATCH ?
          AND k = ?
          AND m.tenant_id = ?
          AND m.project_id = ?
        ORDER BY final_score DESC
        LIMIT ?
    """

    start = time.perf_counter()
    for _ in range(QUERY_RUNS):
        conn.execute(sql, (now, hl, q_bytes, pool, "bench", "bench", limit)).fetchall()
    elapsed = (time.perf_counter() - start) / QUERY_RUNS * 1000
    return elapsed, _exergy_calls // QUERY_RUNS, _decay_calls // QUERY_RUNS


def main():
    print("=" * 76)
    print("CORTEX Memory Microbenchmark — Sovereign Performance Validation")
    print("=" * 76)
    print(f"  Embedding dim: {EMBEDDING_DIM}  |  KNN pool: {KNN_POOL}")
    print(f"  Query runs: {QUERY_RUNS}  |  Limit (K): {LIMIT}")
    print()

    header = (
        f"{'Corpus':>8} | {'Path':>8} | {'Latency':>10} | "
        f"{'Exergy/q':>9} | {'Decay/q':>9} | {'SpeedUp':>8}"
    )
    print(header)
    print("-" * len(header))

    for n in CORPUS_SIZES:
        conn, q_bytes = _setup_db(n)

        old_ms, old_ex, old_dc = _bench_old(conn, q_bytes, LIMIT)
        new_ms, new_ex, new_dc = _bench_new(conn, q_bytes, LIMIT, KNN_POOL)

        ratio = old_ms / new_ms if new_ms > 0 else float("inf")
        cb_reduction = (1 - new_ex / old_ex) * 100 if old_ex > 0 else 0

        print(
            f"{n:>8} | {'OLD':>8} | {old_ms:>9.2f}ms | "
            f"{old_ex:>9} | {old_dc:>9} |"
        )
        print(
            f"{'':>8} | {'NEW':>8} | {new_ms:>9.2f}ms | "
            f"{new_ex:>9} | {new_dc:>9} | {ratio:>6.1f}x"
        )
        print(
            f"{'':>8} |  CB drop | {cb_reduction:>8.1f}%  |"
        )
        print()
        conn.close()

    print("=" * 76)


if __name__ == "__main__":
    main()
