# [C5-REAL] Exergy-Maximized
"""
Migration 030: Typed telemetry tables.

Separates telemetry storage by retrieval kind,
matching the Rust-side RetrievalMetric enum.
"""

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

MIGRATION_ID = 30
MIGRATION_NAME = "typed_telemetry"

UP = """
CREATE TABLE IF NOT EXISTS cortex_raw_metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    value       REAL NOT NULL,
    unit        TEXT NOT NULL,
    source      TEXT NOT NULL,
    timestamp_epoch_ms  INTEGER NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cortex_derived_metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    value       REAL NOT NULL,
    unit        TEXT NOT NULL,
    derivation  TEXT NOT NULL,
    source_metrics TEXT NOT NULL,   -- JSON array of source metric names
    timestamp_epoch_ms  INTEGER NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cortex_narrative_claims (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    claim       TEXT NOT NULL,
    context     TEXT,
    confidence  TEXT,              -- qualitative, not numeric
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_raw_metrics_name 
    ON cortex_raw_metrics(name);
CREATE INDEX IF NOT EXISTS idx_derived_metrics_name 
    ON cortex_derived_metrics(name);
"""

DOWN = """
DROP TABLE IF EXISTS cortex_narrative_claims;
DROP TABLE IF EXISTS cortex_derived_metrics;
DROP TABLE IF EXISTS cortex_raw_metrics;
"""


def _migration_030_typed_telemetry(conn: sqlite3.Connection):
    """Create structured schemas for Raw, Derived, and Narrative telemetry data."""
    conn.executescript(UP)
    logger.info("Migration 030: Created typed retrieval telemetry schemas")
