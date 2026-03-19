import logging
import sqlite3

logger = logging.getLogger("cortex")
_LOG_FMT = "Migration [%03d] %s"


def _migration_027_graph_tenant(conn: sqlite3.Connection) -> None:
    """Add multi-tenant isolation to the Epistemic Graph memory tables."""
    # Check if tenant_id exists in entities
    cursor = conn.execute("PRAGMA table_info(entities)")
    columns = [row[1] for row in cursor.fetchall()]

    if "tenant_id" not in columns:
        conn.execute("ALTER TABLE entities ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'")
        logger.info(_LOG_FMT, 27, "Added tenant_id to entities")

    # Check if tenant_id exists in entity_relations
    cursor = conn.execute("PRAGMA table_info(entity_relations)")
    rel_columns = [row[1] for row in cursor.fetchall()]

    if "tenant_id" not in rel_columns:
        conn.execute(
            "ALTER TABLE entity_relations ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
        )
        logger.info(_LOG_FMT, 27, "Added tenant_id to entity_relations")

    # Drop and recreate indexes to include tenant_id (optional for performance, but necessary for isolation lookup speed)
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_entities_tenant ON entities(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_relations_tenant ON entity_relations(tenant_id);
        """
    )
    logger.info(_LOG_FMT, 27, "Graph multi-tenancy schema migration complete")
