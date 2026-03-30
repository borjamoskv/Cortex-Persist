import logging
import sqlite3
from cortex.auth.schema import AUTH_SCHEMA

logger = logging.getLogger("cortex")


def _migration_028_auth_schema(conn: sqlite3.Connection):
    """Ensure the api_keys table is fully created with all modern columns.
    
    If the table exists but is missing newer columns (like tenant_id, role),
    we alter the table to add them before creating indexes, avoiding OperationalError.
    """
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'"
    )
    exists = cursor.fetchone() is not None

    if not exists:
        logger.info("Migration 028: Creating api_keys table from scratch")
        conn.executescript(AUTH_SCHEMA)
    else:
        logger.info("Migration 028: api_keys table exists, checking columns")
        cursor = conn.execute("PRAGMA table_info(api_keys)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        # Columns that might be missing in older iterations
        expected_cols = {
            "tenant_id": "TEXT NOT NULL DEFAULT 'default'",
            "role": "TEXT NOT NULL DEFAULT 'user'",
            "permissions": "TEXT NOT NULL DEFAULT '[\"read\",\"write\"]'",
            "is_active": "INTEGER NOT NULL DEFAULT 1",
            "rate_limit": "INTEGER NOT NULL DEFAULT 100",
        }

        for col, definition in expected_cols.items():
            if col not in existing_cols:
                logger.info("Migration 028: Adding missing column '%s' to api_keys", col)
                conn.execute(f"ALTER TABLE api_keys ADD COLUMN {col} {definition}")

        # Now safe to run indexes as all columns exist
        conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id)")

    logger.info("Migration 028: Auth schema alignment complete.")
