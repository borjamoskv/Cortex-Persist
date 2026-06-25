# [C5-REAL] Exergy-Maximized
"""
Migration 020: Tombstoning GC columns for Facts.
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


def _migration_020_tombstone(conn: sqlite3.Connection) -> None:
    """Add is_tombstoned and tombstoned_at to facts table."""
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN is_tombstoned INTEGER NOT NULL DEFAULT 0")
    except Exception as exc:
        import logging

        logging.warning("Suppressed exception: %s", exc)
    # Column already exists

    try:
        conn.execute("ALTER TABLE facts ADD COLUMN tombstoned_at TEXT")
    except Exception as exc:
        import logging

        logging.warning("Suppressed exception: %s", exc)
    # Column already exists

    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tombstone ON facts(is_tombstoned)")
