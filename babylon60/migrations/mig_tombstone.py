# [C5-REAL] Exergy-Maximized
"""
Migration 020: Tombstoning GC columns for Facts.
"""

import sqlite3


def _migration_020_tombstone(conn: sqlite3.Connection) -> None:
    """Add is_tombstoned and tombstoned_at to facts table."""
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN is_tombstoned INTEGER NOT NULL DEFAULT 0")
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.warning("Suppressed exception: %s", exc)
    # Column already exists

    try:
        conn.execute("ALTER TABLE facts ADD COLUMN tombstoned_at TEXT")
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.warning("Suppressed exception: %s", exc)
    # Column already exists

    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tombstone ON facts(is_tombstoned)")
