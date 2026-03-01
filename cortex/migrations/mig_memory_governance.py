"""
CORTEX v7 — Migration 019: Memory Governance.

Adds temporal governance columns to the facts table:
- expires_at: TTL support for fact expiry
- last_accessed_at: Audit trail for access tracking
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex.migrations")

_STATEMENTS = [
    # ── Facts: TTL Support ─────────────────────────────────────────
    "ALTER TABLE facts ADD COLUMN expires_at TEXT",
    # ── Facts: Access Audit ────────────────────────────────────────
    "ALTER TABLE facts ADD COLUMN last_accessed_at TEXT",
    # ── Indexes ────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_facts_expires ON facts(expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_facts_last_accessed ON facts(last_accessed_at)",
]


def _migration_019_memory_governance(conn: sqlite3.Connection) -> None:
    """Add expires_at and last_accessed_at columns to facts."""
    for stmt in _STATEMENTS:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                logger.debug("Column already exists, skipping: %s", e)
            else:
                raise
    conn.commit()
    logger.info("Migration 019: Memory Governance applied ✓")
