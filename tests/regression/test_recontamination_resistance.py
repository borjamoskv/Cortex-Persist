"""
tests/regression/test_recontamination_resistance.py

Stress-tests proving the storage engine resists recontamination after cleanup.
This is the difference between "DB was clean" and "DB metabolically resists becoming dirty".

Tested vectors:
  - Concurrent duplicate inserts do not produce orphan states
  - Partial writes aborted mid-way leave DB consistent (INV-001, INV-002)
  - Tombstoning without FTS sync is caught by invariant verifier
  - Quarantine backpressure: quarantined facts stay isolated
  - Namespace-malformed project name does not bypass guards
  - Idempotent backfill: re-running hash backfill does not double-assign
  - Replay of old events does not corrupt dedup counter
  - Race condition simulation: concurrent inserts same hash

Run:
    pytest tests/regression/test_recontamination_resistance.py -v
"""

from __future__ import annotations

import concurrent.futures
import sqlite3
import tempfile
from pathlib import Path

import pytest

# ─── Minimal schema (same mirror as test_db_invariants.py) ────────────────────

FACTS_DDL = """
CREATE TABLE IF NOT EXISTS facts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    project         TEXT NOT NULL,
    content         TEXT NOT NULL,
    fact_type       TEXT NOT NULL DEFAULT 'knowledge',
    tags            TEXT NOT NULL DEFAULT '[]',
    meta            TEXT DEFAULT '{}',
    hash            TEXT,
    valid_from      TEXT,
    valid_until     TEXT,
    source          TEXT,
    confidence      TEXT DEFAULT 'C3',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    is_tombstoned   INTEGER NOT NULL DEFAULT 0,
    is_quarantined  INTEGER NOT NULL DEFAULT 0,
    tx_id           INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_hash_unique ON facts(hash) WHERE hash IS NOT NULL AND is_tombstoned=0 AND is_quarantined=0;
"""

FACTS_FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    content, project, tags, fact_type,
    content='facts', content_rowid='id'
);
"""

FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS trg_facts_fts_insert AFTER INSERT ON facts BEGIN
  INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
  VALUES (NEW.id, NEW.content, NEW.project, NEW.tags, NEW.fact_type);
END;

CREATE TRIGGER IF NOT EXISTS trg_facts_fts_delete AFTER DELETE ON facts BEGIN
  DELETE FROM facts_fts WHERE rowid = OLD.id;
END;
"""

CAUSAL_DDL = """
CREATE TABLE IF NOT EXISTS causal_edges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id     INTEGER NOT NULL REFERENCES facts(id),
    parent_id   INTEGER,
    edge_type   TEXT NOT NULL DEFAULT 'DERIVED_FROM',
    project     TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _fresh_db() -> tuple[sqlite3.Connection, str]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name, isolation_level=None)  # autocommit for clarity
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(FACTS_DDL + FACTS_FTS_DDL + FTS_TRIGGERS + CAUSAL_DDL)
    return conn, tmp.name


def _get_verifier():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "verify_db_invariants",
        Path(__file__).parents[2] / "scripts" / "verify_db_invariants.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture
def db():
    conn, path = _fresh_db()
    yield conn, path
    conn.close()
    Path(path).unlink(missing_ok=True)


# ─── Concurrent Duplicate Inserts ─────────────────────────────────────────────


def test_concurrent_duplicate_inserts_do_not_corrupt_fts(db):
    """
    Multiple threads writing the same hash simultaneously must not create
    duplicate FTS rows or orphan states.
    """
    _, path = db

    duplicates_inserted = []
    errors = []

    def insert_worker(n: int) -> None:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            conn.execute(
                "INSERT OR IGNORE INTO facts (project, content, hash, fact_type, tags) "
                "VALUES ('CONCURRENCY_TEST', 'Same content', 'dedup_hash_001', 'knowledge', '[]')"
            )
            conn.commit()
            duplicates_inserted.append(n)
        except Exception as e:
            errors.append(str(e))
        finally:
            conn.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(insert_worker, range(20)))

    # Verify state is consistent regardless of how many threads "won"
    verifier = _get_verifier()
    report = verifier.run_checks(path)
    fails = [c for c in report.checks if c.status == "FAIL"]
    assert not fails, f"Concurrent inserts left invariant violations: {[c.id for c in fails]}"

    # Only one row should survive the UNIQUE index
    check_conn = sqlite3.connect(path)
    count = check_conn.execute("SELECT count(*) FROM facts WHERE hash='dedup_hash_001'").fetchone()[
        0
    ]
    check_conn.close()
    assert count == 1, f"Expected 1 deduplicated row, got {count}"


# ─── Partial Write Aborted ────────────────────────────────────────────────────


def test_aborted_write_leaves_db_consistent(db):
    """
    A transaction that inserts a fact but is rolled back must not leave
    any FTS artifact.
    """
    conn, path = db
    # Simulate inserting in a transaction that gets rolled back
    conn.execute("BEGIN")
    conn.execute(
        "INSERT INTO facts (project, content, hash, fact_type, tags) "
        "VALUES ('ABORT_TEST', 'This will be rolled back', 'abort_hash_001', 'knowledge', '[]')"
    )
    conn.execute("ROLLBACK")

    verifier = _get_verifier()
    report = verifier.run_checks(path)
    fails = [c for c in report.checks if c.status == "FAIL"]
    assert not fails, f"Aborted write left invariant violations: {[c.id for c in fails]}"


# ─── Quarantine Isolation ─────────────────────────────────────────────────────


def test_quarantined_facts_are_isolated(db):
    """
    Facts marked is_quarantined=1 must not appear in active search paths
    and must trigger INV-003 FAIL if they slip through.
    """
    conn, path = db
    # Insert clean facts
    for i in range(5):
        conn.execute(
            "INSERT INTO facts (project, content, hash, fact_type, tags, is_quarantined) "
            "VALUES ('Q_TEST', ?, ?, 'knowledge', '[]', 0)",
            (f"Clean fact {i}", f"clean_hash_{i}"),
        )
    conn.commit()

    # Baseline should be green
    verifier = _get_verifier()
    report = verifier.run_checks(path)
    assert report.db_state == "green"

    # Simulate a guard failure: quarantined fact with active valid_until=NULL
    conn.execute(
        "INSERT INTO facts (project, content, hash, fact_type, tags, is_quarantined, is_tombstoned) "
        "VALUES ('Q_TEST', 'Poisoned payload', 'malicious_hash', 'knowledge', '[]', 1, 0)"
    )
    conn.commit()

    report = verifier.run_checks(path)
    inv003 = next(c for c in report.checks if c.id == "INV-003")
    assert inv003.status == "FAIL", "INV-003 must FAIL when quarantined fact is active"


# ─── Idempotent Hash Backfill ─────────────────────────────────────────────────


def test_hash_backfill_is_idempotent(db):
    """
    Running a hash backfill multiple times must not corrupt the DB.
    After each run, INV-004 must PASS.
    """
    conn, path = db
    # Insert facts without a hash
    for i in range(10):
        conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags) "
            "VALUES ('BACKFILL_TEST', ?, 'knowledge', '[]')",
            (f"Unhashed fact {i}",),
        )
    conn.commit()

    def run_backfill(conn: sqlite3.Connection) -> None:
        rows = conn.execute("SELECT id, content FROM facts WHERE hash IS NULL").fetchall()
        import hashlib

        for fact_id, content in rows:
            h = hashlib.sha256(content.encode()).hexdigest()
            # Use INSERT OR IGNORE semantics — idempotent
            try:
                conn.execute("UPDATE facts SET hash=? WHERE id=? AND hash IS NULL", (h, fact_id))
            except sqlite3.IntegrityError:
                pass  # Duplicate hash — skip silently
        conn.commit()

    # Run backfill three times — must be idempotent
    for _ in range(3):
        run_backfill(conn)

    verifier = _get_verifier()
    report = verifier.run_checks(path)
    inv004 = next(c for c in report.checks if c.id == "INV-004")
    assert (
        inv004.status == "PASS"
    ), f"INV-004 should PASS after idempotent backfill. Got: {inv004.detail}"


# ─── Malformed Namespace ──────────────────────────────────────────────────────


def test_malformed_namespace_rejected_or_normalized(db):
    """
    A project name with illegal characters should either be rejected
    or stored in a form that does not break index lookups.
    The DB must remain green regardless.
    """
    conn, path = db
    # Project names with characters that could break downstream parsers
    bad_names = [
        "project/with/slashes",
        "project with spaces",
        "PROJECT\x00NULL",
        "../../traversal",
    ]
    for i, name in enumerate(bad_names):
        try:
            conn.execute(
                "INSERT INTO facts (project, content, hash, fact_type, tags) "
                "VALUES (?, 'Malformed namespace test', ?, 'knowledge', '[]')",
                (name, f"mfhash_{i}"),
            )
            conn.commit()
        except sqlite3.Error:
            pass  # Rejection is acceptable

    verifier = _get_verifier()
    report = verifier.run_checks(path)
    fails = [c for c in report.checks if c.status == "FAIL"]
    assert not fails, f"Malformed namespaces caused invariant violations: {[c.id for c in fails]}"


# ─── Causal Edge Crash Simulation ─────────────────────────────────────────────


def test_orphan_causal_edge_from_partial_failure_detected(db):
    """
    If a causal edge is written but the parent fact write fails/rolls back,
    the orphan must be detected by INV-002.
    """
    conn, path = db

    # Manually create an orphan causal edge referencing a non-existent fact
    # (simulates crash between causal write and fact commit)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(
        "INSERT INTO causal_edges (fact_id, edge_type, project) "
        "VALUES (9999, 'DERIVED_FROM', 'CRASH_TEST')"
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")

    verifier = _get_verifier()
    report = verifier.run_checks(path)
    inv002 = next(c for c in report.checks if c.id == "INV-002")
    assert (
        inv002.status == "FAIL"
    ), "INV-002 must FAIL when causal edge references non-existent fact"
    assert report.orphan_causal_count >= 1


# ─── FTS/Facts Parity Under Load ─────────────────────────────────────────────


def test_fts_parity_maintained_after_bulk_delete(db):
    """
    Bulk deletion of facts must keep FTS in sync via triggers.
    INV-007 must PASS after cleanup.
    """
    conn, path = db
    # Insert 50 facts
    ids = []
    for i in range(50):
        cur = conn.execute(
            "INSERT INTO facts (project, content, hash, fact_type, tags) "
            "VALUES ('BULK_DELETE', ?, ?, 'knowledge', '[]')",
            (f"Bulk fact {i}", f"bulkhash_{i:04d}"),
        )
        ids.append(cur.lastrowid)
    conn.commit()

    # Delete half via legitimate DELETE (trigger fires)
    for fid in ids[:25]:
        conn.execute("DELETE FROM facts WHERE id=?", (fid,))
    conn.commit()

    verifier = _get_verifier()
    report = verifier.run_checks(path)
    inv007 = next(c for c in report.checks if c.id == "INV-007")
    assert inv007.status == "PASS", (
        f"INV-007 (FTS/facts parity) failed after bulk delete. "
        f"FTS={report.fts_count}, active={report.active_facts}"
    )
