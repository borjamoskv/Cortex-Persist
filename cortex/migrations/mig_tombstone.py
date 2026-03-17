"""
CORTEX v5.0 — Migration 020: Tombstoning GC columns for Facts.
"""

import sqlite3


def _migration_020_tombstone(conn: sqlite3.Connection) -> None:
    """Add is_tombstoned and tombstoned_at to facts table."""
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN is_tombstoned INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute("ALTER TABLE facts ADD COLUMN tombstoned_at TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tombstone ON facts(is_tombstoned)")
