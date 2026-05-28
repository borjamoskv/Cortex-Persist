import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_016_add_fact_hash(conn: sqlite3.Connection):
    """Add hash column to facts table for deduplication (Wave 4: Global Integrity)."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()}
    if "hash" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN hash TEXT")
        logger.info("Migration 016: Added 'hash' column to facts")

    # Add unique partial index for dedup (skip if already exists)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_hash "
        "ON facts(tenant_id, project, hash) WHERE hash IS NOT NULL AND valid_until IS NULL"
    )
    logger.info("Migration 016: idx_facts_hash index ensured")

    # Note: existing encrypted rows keep hash=NULL (safe: unique index only applies to
    # hash IS NOT NULL rows). New facts will always get hashed. Legacy rows won't dedup
    # against each other by hash, which is acceptable — they existed before dedup was
    # enforced. No backfill needed for encrypted content.
