# [C5-REAL] Exergy-Maximized
"""
Migration 029: Hebbian Multiplier columns.

Adds access_count and last_accessed_at to the facts table to track retrieval frequency.
Protects against silent structural erosion.

DOWNGRADE TARGET: 28
"""

import sqlite3

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
