import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_015_tenant_unification(conn: sqlite3.Connection):
    """Unify tenant_id across all core tables (Sovereign Level).

    DYNAMIC DETECTION: Instead of hardcoding, we introspect the schema
    and apply the tenant column to any table that doesn't have it.
    """
    # Get all user tables, excluding sqlite internals and FTS virtual/shadow tables
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' "
        "AND name NOT LIKE '%_fts%'"
    )
    all_tables = [row[0] for row in cursor.fetchall()]

    for table in all_tables:
        # Check for column
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = {row[1] for row in cursor.fetchall()}

        if "tenant_id" not in columns:
            logger.info("Sovereign Wave 015: Adding 'tenant_id' to %s", table)
            try:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
                )
            except sqlite3.OperationalError as e:
                # Handle cases where table might be virtual or restricted
                logger.debug("Skipping column add for %s: %s", table, e)

    # Re-verify and ensure indices on critical paths
    critical_indices = {
        "idx_tx_tenant": "transactions",
        "idx_ep_tenant": "episodes",
        "idx_ctx_snap_tenant": "context_snapshots",
        "idx_facts_tenant": "facts",
        "idx_sess_tenant": "sessions"
    }

    for idx, table in critical_indices.items():
        if table in all_tables:
            conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {table}(tenant_id)")

    logger.info("Migration 015: Sovereign dynamic unification complete.")
