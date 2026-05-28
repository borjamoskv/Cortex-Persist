"""
Migration: Simplify Facts Table
Collapses non-essential columns into the `metadata` JSON field to reduce DB entropy.

.. warning:: DESTRUCTIVE MIGRATION
   This migration drops columns from the facts table. It is NOT reversible.
   The live DB has 32 columns; this migration collapses to 11.
   DO NOT RUN without explicit operator approval and a backup.
"""

import logging
import sqlite3

logger = logging.getLogger("cortex")


def migrate_simplify_facts(conn: sqlite3.Connection) -> None:
    """Migrates the facts table, moving deprecated columns into the meta JSON field."""
    logger.info("Migrating facts table: simplifying structure and moving fields to `metadata`...")

    # 1. Create the new facts table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id   TEXT NOT NULL DEFAULT 'default',
            project     TEXT NOT NULL,
            content     TEXT NOT NULL,
            fact_type   TEXT NOT NULL DEFAULT 'knowledge',
            tags        TEXT NOT NULL DEFAULT '[]',
            metadata    TEXT DEFAULT '{}',
            hash        TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
            is_tombstoned INTEGER NOT NULL DEFAULT 0
        )
    """)

    # 2. Copy data, merging dropped columns into the `meta` JSON object
    # Using json_set to insert values only if they were not already present or to preserve them.
    # We take care to handle NULLs correctly by only including them if they exist or dropping if we want,
    # but json_set handles NULLs by inserting JSON null.
    conn.execute("""
        INSERT INTO facts_new (
            id, tenant_id, project, content, fact_type, tags, hash, created_at, updated_at, is_tombstoned, metadata
        )
        SELECT 
            id, tenant_id, project, content, fact_type, tags, hash, created_at, updated_at, is_tombstoned,
            json_set(
                COALESCE(metadata, '{}'),
                '$.confidence', confidence,
                '$.cognitive_layer', cognitive_layer,
                '$.parent_decision_id', parent_decision_id,
                '$.valid_from', valid_from,
                '$.valid_until', valid_until,
                '$.source', source,
                '$.consensus_score', consensus_score,
                '$.signature', signature,
                '$.signer_pubkey', signer_pubkey,
                '$.is_quarantined', is_quarantined,
                '$.quarantined_at', quarantined_at,
                '$.quarantine_reason', quarantine_reason,
                '$.tx_id', tx_id,
                '$.tombstoned_at', tombstoned_at
            )
        FROM facts
    """)

    # 3. Drop the old table and rename the new one
    conn.execute("DROP TABLE facts")
    conn.execute("ALTER TABLE facts_new RENAME TO facts")

    # 4. Recreate indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tenant ON facts(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_project ON facts(project)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_proj_type ON facts(project, fact_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tombstone ON facts(is_tombstoned)")

    logger.info("Migration simplify facts completed successfully.")
