# [C5-REAL] Exergy-Maximized
"""Migration 021: Solid-State Substrate (entity_events table).

Creates the append-only, hash-chained entity_events table
that serves as the cryptographic source of truth for all
fact state mutations. See cortex.engine.mutation_engine.
"""

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


def _migration_021_solid_state(conn: sqlite3.Connection) -> None:
    """Create entity_events table and indexes."""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entity_events (
                id              TEXT PRIMARY KEY,
                entity_id       INTEGER NOT NULL,
                tenant_id       TEXT NOT NULL DEFAULT 'default',
                event_type      TEXT NOT NULL,
                payload         TEXT NOT NULL DEFAULT '{}',
                timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
                prev_hash       TEXT NOT NULL DEFAULT 'GENESIS',
                signature       TEXT NOT NULL,
                signer          TEXT NOT NULL DEFAULT '',
                schema_version  TEXT NOT NULL DEFAULT '1'
            )
        """)
    except Exception as exc:
        import logging

        logging.warning("Suppressed exception: %s", exc)
    # Table already exists

    conn.execute("CREATE INDEX IF NOT EXISTS idx_ee_entity ON entity_events(entity_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ee_tenant ON entity_events(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ee_type ON entity_events(event_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ee_timestamp ON entity_events(timestamp)")
