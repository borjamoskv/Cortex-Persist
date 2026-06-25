# [C5-REAL] Exergy-Maximized
"""
Migration 029: Hebbian Multiplier columns.

Adds access_count and last_accessed_at to the facts table to track retrieval frequency.
Protects against silent structural erosion.

DOWNGRADE TARGET: 28
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


def _migration_029_hebbian_multiplier(conn: sqlite3.Connection) -> None:
    """Add access_count and last_accessed_at columns."""
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN access_count INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN last_accessed_at TEXT")
    except sqlite3.OperationalError:
        pass
