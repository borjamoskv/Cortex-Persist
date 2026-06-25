# [C5-REAL] Exergy-Maximized
from __future__ import annotations




import sqlite3


from cortex.database.schema import SCHEMA_VERSION
from legacy_research.migrations import get_current_version, run_migrations
from legacy_research.migrations.registry import MIGRATIONS




def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _column_info(conn: sqlite3.Connection, table: str, column: str) -> sqlite3.Row:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        f"SELECT * FROM pragma_table_info('{table}') WHERE name = ?",
        (column,),
    ).fetchone()
    assert row is not None
    return row


def test_fresh_schema_has_tenant_scoped_merkle_roots() -> None:
    conn = sqlite3.connect(":memory:")
    applied = run_migrations(conn)

    assert applied == 0
    assert get_current_version(conn) == MIGRATIONS[-1][0]
    assert "tenant_id" in _columns(conn, "merkle_roots")
    tenant_id = _column_info(conn, "merkle_roots", "tenant_id")
    assert tenant_id["notnull"] == 1
    assert tenant_id["dflt_value"] == "'__global__'"
    assert "tenant_id" in _columns(conn, "ledger_replay_admissions")
    assert "nonce" in _columns(conn, "ledger_replay_admissions")
    assert SCHEMA_VERSION == "5.4.3"


def test_migration_025_adds_merkle_tenant_scope_without_data_loss() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript("""

        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        );
        INSERT INTO schema_version (version, description) VALUES (24, 'pre forensic baseline');
        CREATE TABLE merkle_roots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            root_hash       TEXT NOT NULL,
            tx_start_id     INTEGER NOT NULL,
            tx_end_id       INTEGER NOT NULL,
            tx_count        INTEGER NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO merkle_roots (root_hash, tx_start_id, tx_end_id, tx_count)
        VALUES ('root-a', 1, 3, 3);
        CREATE TABLE facts (id INTEGER PRIMARY KEY, fact_hash TEXT UNIQUE);
        CREATE TABLE causal_edges (id INTEGER PRIMARY KEY, fact_hash TEXT UNIQUE);
    """)

    applied = run_migrations(conn)

    assert applied == len([m for m in MIGRATIONS if m[0] > 24])
    assert get_current_version(conn) == MIGRATIONS[-1][0]
    assert "tenant_id" in _columns(conn, "merkle_roots")
    tenant_id = _column_info(conn, "merkle_roots", "tenant_id")
    assert tenant_id["notnull"] == 1
    assert tenant_id["dflt_value"] == "'__global__'"
    row = conn.execute(
        "SELECT tenant_id, root_hash, tx_start_id, tx_end_id, tx_count FROM merkle_roots"
    ).fetchone()
    assert tuple(row) == ("__global__", "root-a", 1, 3, 3)
    indexes = {row[1] for row in conn.execute("PRAGMA index_list(merkle_roots)").fetchall()}
    assert "idx_merkle_tenant_range" in indexes


def test_migration_registry_tracks_forensic_ledger_schema_version() -> None:
    versions = [version for version, _description, _func in MIGRATIONS]
    assert versions[-1] == MIGRATIONS[-1][0]
    assert versions == sorted(versions)
    assert len(versions) == len(set(versions))


def test_migration_026_adds_replay_admission_table_and_tenant_scoped_uniques() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript("""

        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        );
        INSERT INTO schema_version (version, description) VALUES (25, 'pre replay baseline');
        CREATE TABLE facts (id INTEGER PRIMARY KEY, fact_hash TEXT UNIQUE);
        CREATE TABLE causal_edges (id INTEGER PRIMARY KEY, fact_hash TEXT UNIQUE);
    """)

    applied = run_migrations(conn)

    assert applied == len([m for m in MIGRATIONS if m[0] > 25])
    assert get_current_version(conn) == MIGRATIONS[-1][0]
    columns = _columns(conn, "ledger_replay_admissions")
    assert {
        "tenant_id",
        "event_id",
        "nonce",
        "request_hash",
        "payload_hash",
        "ledger_event_id",
    } <= columns
    indexes = {
        row[1]: bool(row[2])
        for row in conn.execute("PRAGMA index_list(ledger_replay_admissions)").fetchall()
    }
    assert indexes["ux_ledger_replay_tenant_event_id"] is True
    assert indexes["ux_ledger_replay_tenant_nonce"] is True
