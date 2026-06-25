# [C5-REAL] Exergy-Maximized
import logging
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
        "idx_sess_tenant": "sessions",
        "idx_graph_ent_tenant": "graph_entities",
        "idx_graph_rel_tenant": "graph_relationships",
    }

    for idx, table in critical_indices.items():
        if table in all_tables:
            conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {table}(tenant_id)")

    logger.info("Migration 015: Sovereign dynamic unification complete.")
