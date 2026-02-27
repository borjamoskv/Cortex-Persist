"""CORTEX Auth — SQL Schema definitions."""

AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    key_hash    TEXT NOT NULL UNIQUE,
    key_prefix  TEXT NOT NULL,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    role        TEXT NOT NULL DEFAULT 'user',
    permissions TEXT NOT NULL DEFAULT '["read","write"]',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_used   TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    rate_limit  INTEGER NOT NULL DEFAULT 100
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
"""

SQL_INSERT_KEY = """
    INSERT INTO api_keys (name, key_hash, key_prefix, tenant_id, role, permissions, rate_limit)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""
