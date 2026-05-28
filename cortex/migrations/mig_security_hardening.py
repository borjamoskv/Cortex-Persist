"""
CORTEX v5.2 — Migration 018: Security Hardening (Cibercentro Mitigations).

Adds quarantine support to facts and TTL support to ghosts.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex.migrations")

_STATEMENTS = [
    # ── Facts: Quarantine Support ──────────────────────────────────
    "ALTER TABLE facts ADD COLUMN is_quarantined INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE facts ADD COLUMN quarantined_at TEXT",
    "ALTER TABLE facts ADD COLUMN quarantine_reason TEXT",
    "CREATE INDEX IF NOT EXISTS idx_facts_quarantine ON facts(is_quarantined)",
    # ── Ghosts: TTL Support ────────────────────────────────────────
    "ALTER TABLE ghosts ADD COLUMN expires_at TEXT",
    "CREATE INDEX IF NOT EXISTS idx_ghosts_expires ON ghosts(expires_at)",
    # ── Update dedup unique index to exclude quarantined facts ─────
    "DROP INDEX IF EXISTS idx_facts_hash",
    (
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_hash "
        "ON facts(tenant_id, project, hash) "
        "WHERE hash IS NOT NULL AND valid_until IS NULL AND is_quarantined = 0"
    ),
]


def _migration_018_security_hardening(conn: sqlite3.Connection) -> None:
    """Add quarantine columns to facts and TTL to ghosts."""
    for stmt in _STATEMENTS:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                logger.debug("Column already exists, skipping: %s", e)
            else:
                raise
    conn.commit()
    logger.info("Migration 018: Security hardening applied ✓")
