# [C5-REAL] Exergy-Maximized
import logging
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------

logger = logging.getLogger("cortex")


def _migration_010_immutable_ledger(conn: sqlite3.Connection):
    """Add tables for hierarchical immutable ledger (Merkle Roots)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS vote_ledger (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id       TEXT NOT NULL DEFAULT 'default',
            fact_id         INTEGER NOT NULL REFERENCES facts(id),
            agent_id        TEXT NOT NULL,
            vote            INTEGER NOT NULL,
            vote_weight     REAL NOT NULL,
            prev_hash       TEXT NOT NULL,
            hash            TEXT NOT NULL,
            timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
            signature       TEXT,
            UNIQUE(hash)
        );
        CREATE INDEX IF NOT EXISTS idx_vote_ledger_fact ON vote_ledger(fact_id);
        CREATE INDEX IF NOT EXISTS idx_vote_ledger_agent ON vote_ledger(agent_id);
        CREATE INDEX IF NOT EXISTS idx_vote_ledger_timestamp ON vote_ledger(timestamp);

        CREATE TABLE IF NOT EXISTS merkle_roots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            root_hash       TEXT NOT NULL,
            tx_start_id     INTEGER NOT NULL,
            tx_end_id       INTEGER NOT NULL,
            tx_count        INTEGER NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            signature       TEXT,
            external_proof  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_merkle_range ON merkle_roots(tx_start_id, tx_end_id);

        CREATE TABLE IF NOT EXISTS integrity_checks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            check_type      TEXT NOT NULL, -- 'full', 'chain', 'merkle'
            status          TEXT NOT NULL, -- 'ok', 'violation'
            details         TEXT,          -- JSON list of violations
            started_at      TEXT NOT NULL,
            completed_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_exports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            export_type     TEXT NOT NULL,
            filename        TEXT NOT NULL,
            file_hash       TEXT NOT NULL,
            tx_start_id     INTEGER NOT NULL,
            tx_end_id       INTEGER NOT NULL,
            exported_at     TEXT NOT NULL DEFAULT (datetime('now')),
            exported_by     TEXT NOT NULL
        );
    """)
    logger.info("Migration 010: Created Immutable Ledger tables")


def _migration_011_link_facts_to_tx(conn: sqlite3.Connection):
    """Link facts and votes to the transaction ledger via tx_id."""
    # 1. Add tx_id to facts
    columns_facts = {row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()}
    if "tx_id" not in columns_facts:
        conn.execute("ALTER TABLE facts ADD COLUMN tx_id INTEGER REFERENCES transactions(id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tx_id ON facts(tx_id)")
        logger.info("Migration 011: Added 'tx_id' column to facts")

    # 2. Add tx_id to consensus_votes_v2
    columns_votes = {
        row[1] for row in conn.execute("PRAGMA table_info(consensus_votes_v2)").fetchall()
    }
    if "tx_id" not in columns_votes:
        conn.execute(
            "ALTER TABLE consensus_votes_v2 ADD COLUMN tx_id INTEGER REFERENCES transactions(id)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_v2_tx_id ON consensus_votes_v2(tx_id)")
        logger.info("Migration 011: Added 'tx_id' column to consensus_votes_v2")

    # 3. Best effort: Try to backfill tx_id using created_at/timestamp
    # This matches the fact's created_at with the transaction's timestamp (approximate)
    conn.execute("""
        UPDATE facts
        SET tx_id = (
            SELECT id FROM transactions
            WHERE transactions.timestamp <= facts.created_at
            ORDER BY transactions.timestamp DESC, transactions.id DESC LIMIT 1
        )
        WHERE tx_id IS NULL
    """)
    conn.commit()


def _migration_012_ghosts_table(conn: sqlite3.Connection):
    """Create the ghosts table for tracking dangling references."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ghosts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            reference       TEXT NOT NULL,
            context         TEXT,
            project         TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'open',
            detected_at     TEXT NOT NULL,
            resolved_at     TEXT,
            target_id       INTEGER REFERENCES entities(id),
            confidence      REAL DEFAULT 0.0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ghosts_project ON ghosts(project)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ghosts_status ON ghosts(status)")


def _migration_014_vote_ledger_refinement(conn: sqlite3.Connection):
    """Wave 5: Refine Immutable Ledger and sync with Sovereign spec."""
    # 1. Create vote_ledger if missing (correcting Migration 010 debt)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vote_ledger (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id       TEXT NOT NULL DEFAULT 'default',
            fact_id         INTEGER NOT NULL REFERENCES facts(id),
            agent_id        TEXT NOT NULL,
            vote            INTEGER NOT NULL,
            vote_weight     REAL NOT NULL,
            prev_hash       TEXT NOT NULL,
            hash            TEXT NOT NULL,
            timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
            signature       TEXT,
            UNIQUE(hash)
        )
    """)
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_vote_ledger_fact ON vote_ledger(fact_id);
        CREATE INDEX IF NOT EXISTS idx_vote_ledger_agent ON vote_ledger(agent_id);
        CREATE INDEX IF NOT EXISTS idx_vote_ledger_timestamp ON vote_ledger(timestamp);
    """)

    # 2. Create vote_merkle_roots (Wave 5 specific naming)
    # We keep existing merkle_roots for backwards compatibility or potentially migration later
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vote_merkle_roots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id       TEXT NOT NULL DEFAULT 'default',
            root_hash       TEXT NOT NULL,
            vote_start_id   INTEGER NOT NULL,
            vote_end_id     INTEGER NOT NULL,
            vote_count      INTEGER NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(root_hash)
        )
    """)
    logger.info("Migration 014: Refined Immutable Ledger (vote_ledger + vote_merkle_roots)")


# DOWNGRADE TARGET: 24
# Rollback strategy: this is additive and preserves checkpoint data. A downgrade
# should leave the tenant_id column in place; older readers ignore unknown columns.
def _migration_025_tenant_bound_merkle_roots(conn: sqlite3.Connection):
    """Add tenant scope metadata to transaction Merkle checkpoints."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(merkle_roots)").fetchall()}
    if "tenant_id" not in columns:
        conn.execute(
            "ALTER TABLE merkle_roots ADD COLUMN tenant_id TEXT NOT NULL DEFAULT '__global__'"
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_merkle_tenant_range "
        "ON merkle_roots(tenant_id, tx_start_id, tx_end_id)"
    )
    logger.info("Migration 025: Added tenant scope metadata to merkle_roots")


# DOWNGRADE TARGET: 25
# Rollback strategy: this is an additive online-admission table. Downgrades may
# leave ledger_replay_admissions in place; older readers ignore the table, and
# dropping it would remove replay evidence needed to audit live admission.
def _migration_026_ledger_replay_admission(conn: sqlite3.Connection):
    """Add tenant-scoped replay admission reservations for strict ledger writes."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ledger_replay_admissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            nonce TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            ledger_event_id TEXT NOT NULL,
            actor_key_id TEXT NOT NULL,
            action TEXT NOT NULL,
            issued_at TEXT NOT NULL,
            accepted_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_ledger_replay_tenant_event_id
            ON ledger_replay_admissions(tenant_id, event_id);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_ledger_replay_tenant_nonce
            ON ledger_replay_admissions(tenant_id, nonce);
        CREATE INDEX IF NOT EXISTS idx_ledger_replay_tenant_accepted
            ON ledger_replay_admissions(tenant_id, accepted_at);
    """)
    logger.info("Migration 026: Added ledger replay admission reservations")
