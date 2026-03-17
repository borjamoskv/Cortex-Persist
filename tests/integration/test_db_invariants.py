"""
tests/integration/test_db_invariants.py

Integration tests for CORTEX DB invariants.
Provisions an in-memory SQLite database with the full schema and:
  - verifies all hard invariants pass on a clean DB
  - verifies invariants FAIL when deliberately violated
  - ensures the verify_db_invariants script returns exit code 0

Run:
    pytest tests/integration/test_db_invariants.py -v
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

# ─── Minimal schema for testing (mirrors real schema without circular imports) ─


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
"""

FACTS_FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    content, project, tags, fact_type
);
"""

FTS_TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS trg_facts_fts_insert AFTER INSERT ON facts BEGIN
  INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
  VALUES (NEW.id, NEW.content, NEW.project, NEW.tags, NEW.fact_type);
END;
"""

FTS_TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS trg_facts_fts_delete AFTER DELETE ON facts BEGIN
  DELETE FROM facts_fts WHERE rowid = OLD.id;
END;
"""

CAUSAL_EDGES_DDL = """
CREATE TABLE IF NOT EXISTS causal_edges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id     INTEGER NOT NULL,
    parent_id   INTEGER,
    signal_id   INTEGER,
    edge_type   TEXT NOT NULL DEFAULT 'DERIVED_FROM',
    project     TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _fresh_db() -> tuple[sqlite3.Connection, str]:
    """Return an in-memory connection and a temp file path for the verifier script."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.executescript(
        FACTS_DDL + FACTS_FTS_DDL + FTS_TRIGGER_INSERT + FTS_TRIGGER_DELETE + CAUSAL_EDGES_DDL
    )
    return conn, tmp.name


def _insert_fact(conn: sqlite3.Connection, **kwargs) -> int:
    defaults = {
        "tenant_id": "default",
        "project": "TEST_PROJECT",
        "content": "A test fact",
        "fact_type": "knowledge",
        "tags": "[]",
        "hash": "abc123",
        "is_tombstoned": 0,
        "is_quarantined": 0,
    }
    defaults.update(kwargs)
    cur = conn.execute(
        "INSERT INTO facts (tenant_id, project, content, fact_type, tags, hash, is_tombstoned, is_quarantined) "
        "VALUES (:tenant_id, :project, :content, :fact_type, :tags, :hash, :is_tombstoned, :is_quarantined)",
        defaults,
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


# ─── Import the verifier ───────────────────────────────────────────────────────


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


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestCleanDatabasePassesAllInvariants:
    """An empty or clean database should pass every hard invariant."""

    def test_empty_db_is_green(self, db, tmp_path):
        conn, path = db
        verifier = _get_verifier()
        report = verifier.run_checks(path)
        fails = [c for c in report.checks if c.status == "FAIL"]
        assert fails == [], f"Unexpected failures on clean DB: {[c.id for c in fails]}"
        assert report.db_state == "green"

    def test_populated_clean_db_is_green(self, db, tmp_path):
        conn, path = db
        for i in range(10):
            _insert_fact(conn, content=f"Fact number {i}", hash=f"hash{i:04d}")
        verifier = _get_verifier()
        report = verifier.run_checks(path)
        assert (
            report.db_state == "green"
        ), f"Expected green, got {report.db_state}. Fails: {[c.id for c in report.checks if c.status=='FAIL']}"


class TestHardInvariantViolations:
    """Deliberately violate each hard invariant and confirm FAIL is detected."""

    def test_inv001_orphan_fts_detected(self, db):
        conn, path = db
        # Directly insert into FTS bypassing the main table to simulate an FTS desync orphan
        conn.execute(
            "INSERT INTO facts_fts(rowid, content, project, tags, fact_type) "
            "VALUES (99999, 'Orphan FTS content', 'TEST', '[]', 'knowledge')"
        )
        conn.commit()
        verifier = _get_verifier()
        report = verifier.run_checks(path)
        inv001 = next(c for c in report.checks if c.id == "INV-001")
        assert inv001.status == "FAIL", "INV-001 should FAIL when FTS orphan exists"

    def test_inv002_orphan_causal_edge_detected(self, db):
        conn, path = db
        # Insert a fact, record its id, then delete the fact but keep the causal edge
        fact_id = _insert_fact(conn, content="Causal source")
        conn.execute(
            "INSERT INTO causal_edges (fact_id, edge_type, project) VALUES (?, 'DERIVED_FROM', 'TEST_PROJECT')",
            (fact_id,),
        )
        conn.execute("DELETE FROM facts WHERE id=?", (fact_id,))
        conn.commit()
        verifier = _get_verifier()
        report = verifier.run_checks(path)
        inv002 = next(c for c in report.checks if c.id == "INV-002")
        assert (
            inv002.status == "FAIL"
        ), "INV-002 should FAIL when causal edge references deleted fact"

    def test_inv003_active_quarantined_fact_detected(self, db):
        conn, path = db
        # A quarantined fact with no valid_until (active range) and not tombstoned
        _insert_fact(conn, content="Bad payload", is_quarantined=1, is_tombstoned=0)
        verifier = _get_verifier()
        report = verifier.run_checks(path)
        inv003 = next(c for c in report.checks if c.id == "INV-003")
        assert inv003.status == "FAIL", "INV-003 should FAIL for quarantined fact in active index"

    def test_inv004_unhashed_active_fact_detected(self, db):
        conn, path = db
        _insert_fact(conn, content="No hash here", hash=None)
        verifier = _get_verifier()
        report = verifier.run_checks(path)
        inv004 = next(c for c in report.checks if c.id == "INV-004")
        assert inv004.status in ("WARN", "FAIL"), "INV-004 should not PASS when hash is NULL"

    def test_inv006_tombstoned_fact_in_fts_detected(self, db):
        conn, path = db
        # Insert a fact, tombstone it manually without FTS delete trigger catching it
        # (simulate trigger bug or migration gap)
        fact_id = _insert_fact(conn, content="Will be buried")
        # Tombstone directly in facts only, bypassing FTS trigger
        conn.execute("UPDATE facts SET is_tombstoned=1 WHERE id=?", (fact_id,))
        conn.commit()
        # FTS should still have the row (trigger only fires on DELETE not UPDATE)
        verifier = _get_verifier()
        report = verifier.run_checks(path)
        inv006 = next(c for c in report.checks if c.id == "INV-006")
        assert inv006.status == "FAIL", "INV-006 should FAIL when tombstoned fact still in FTS"


class TestVerifierScript:
    """Smoke-test the CLI entry point via main()."""

    def test_main_returns_0_on_clean_db(self, db, tmp_path):
        conn, path = db
        _insert_fact(conn, content="Clean fact")
        verifier = _get_verifier()
        out = tmp_path / "report.json"
        result = verifier.main(["--db", path, "--out", str(out)])
        assert result == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["db_state"] == "green"

    def test_main_returns_1_on_fail(self, db, tmp_path):
        conn, path = db
        # Create an orphan causal edge
        conn.execute(
            "INSERT INTO causal_edges (fact_id, edge_type, project) VALUES (99999, 'DERIVED_FROM', 'X')"
        )
        conn.commit()
        verifier = _get_verifier()
        out = tmp_path / "report.json"
        result = verifier.main(["--db", path, "--out", str(out)])
        assert result == 1
