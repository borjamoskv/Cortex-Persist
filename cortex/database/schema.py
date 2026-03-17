"""
CORTEX v5.0 — SQLite Schema Definitions.

All tables, indexes, and virtual tables for the sovereign memory engine.
Extended tables (consensus, episodes, signals, entity_events, evolution_state)
live in schema_extensions.py to satisfy the Landauer LOC barrier.
"""

# Re-export extended tables for backward compat
from cortex.database.schema_extensions import (
    CREATE_AGENTS,
    CREATE_CONTEXT_SNAPSHOTS,
    CREATE_CONTEXT_SNAPSHOTS_INDEX,
    CREATE_ENTITY_EVENTS,
    CREATE_ENTITY_EVENTS_INDEXES,
    CREATE_EPISODES,
    CREATE_EPISODES_FTS,
    CREATE_EPISODES_INDEXES,
    CREATE_EVOLUTION_STATE,
    CREATE_EVOLUTION_STATE_INDEX,
    CREATE_FACTS_FTS,
    CREATE_MERKLE_ROOTS,
    CREATE_OUTCOMES,
    CREATE_PROCEDURAL_ENGRAMS,
    CREATE_RWC_INDEXES,
    CREATE_SIGNALS,
    CREATE_SIGNALS_INDEXES,
    CREATE_TRUST_EDGES,
    CREATE_VOTES,
    CREATE_VOTES_V2,
    EXTENSION_SCHEMA,
)

__all__ = [
    "ALL_SCHEMA",
    "CREATE_AGENTS",
    "CREATE_COMPACTION_LOG",
    "CREATE_CONTEXT_SNAPSHOTS",
    "CREATE_CONTEXT_SNAPSHOTS_INDEX",
    "CREATE_EMBEDDINGS",
    "CREATE_ENTITY_EVENTS",
    "CREATE_ENTITY_EVENTS_INDEXES",
    "CREATE_EVOLUTION_STATE",
    "CREATE_EVOLUTION_STATE_INDEX",
    "CREATE_SPECULAR_EMBEDDINGS",
    "CREATE_EPISODES",
    "CREATE_EPISODES_FTS",
    "CREATE_EPISODES_INDEXES",
    "CREATE_FACTS",
    "CREATE_FACTS_INDEXES",
    "CREATE_GHOSTS",
    "CREATE_GHOSTS_INDEX",
    "CREATE_HEARTBEATS",
    "CREATE_HEARTBEATS_INDEX",
    "CREATE_META",
    "CREATE_OUTCOMES",
    "CREATE_RWC_INDEXES",
    "CREATE_SESSIONS",
    "CREATE_SIGNALS",
    "CREATE_SIGNALS_INDEXES",
    "CREATE_TIME_ENTRIES",
    "CREATE_TIME_ENTRIES_INDEX",
    "CREATE_TRANSACTIONS",
    "CREATE_TRANSACTIONS_INDEX",
    CREATE_TRUST_EDGES,
    CREATE_VOTES,
    CREATE_VOTES_V2,
    CREATE_PROCEDURAL_ENGRAMS,
    CREATE_FACTS_FTS,
    CREATE_MERKLE_ROOTS,
    "CREATE_TENANTS",
    "CREATE_THREAT_INTEL",
    "CREATE_THREAT_INTEL_INDEXES",
    "SCHEMA_VERSION",
    "get_init_meta",
]

SCHEMA_VERSION = "5.3.0"

# ─── Core Facts Table ────────────────────────────────────────────────
CREATE_FACTS = """
CREATE TABLE IF NOT EXISTS facts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    project     TEXT NOT NULL,
    content     TEXT NOT NULL,
    fact_type   TEXT NOT NULL DEFAULT 'knowledge',
    tags        TEXT NOT NULL DEFAULT '[]',
    meta        TEXT DEFAULT '{}',
    hash        TEXT,
    valid_from  TEXT,
    valid_until TEXT,
    source      TEXT,
    confidence  TEXT DEFAULT 'C3',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    is_tombstoned INTEGER NOT NULL DEFAULT 0,
    is_quarantined INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_FACTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_facts_tenant ON facts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_facts_project ON facts(project);
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_proj_type ON facts(project, fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_tombstone ON facts(is_tombstoned);
CREATE INDEX IF NOT EXISTS idx_facts_tenant_valid ON facts(tenant_id, valid_until);
CREATE INDEX IF NOT EXISTS idx_facts_proj_valid ON facts(project, valid_until);
"""

# ─── Vector Embeddings (sqlite-vec) ──────────────────────────────────
CREATE_EMBEDDINGS = """
CREATE VIRTUAL TABLE IF NOT EXISTS fact_embeddings USING vec0(
    fact_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);
"""

# ─── Specular Memory (HDC 8k) ────────────────────────────────────────
CREATE_SPECULAR_EMBEDDINGS = """
CREATE VIRTUAL TABLE IF NOT EXISTS specular_embeddings USING vec0(
    fact_id INTEGER PRIMARY KEY,
    embedding FLOAT[8000]
);
"""

# ─── Sessions Log ────────────────────────────────────────────────────
CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    date            TEXT NOT NULL,
    focus           TEXT NOT NULL DEFAULT '[]',
    summary         TEXT NOT NULL,
    conversations   INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# ─── Transaction Ledger ───────────────────────────────────────────────
CREATE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    project     TEXT NOT NULL,
    action      TEXT NOT NULL,
    detail      TEXT,
    prev_hash   TEXT,
    hash        TEXT NOT NULL,
    timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_TRANSACTIONS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_tx_tenant ON transactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tx_project ON transactions(project);
CREATE INDEX IF NOT EXISTS idx_tx_action ON transactions(action);

CREATE TRIGGER IF NOT EXISTS prevent_tx_update BEFORE UPDATE ON transactions
BEGIN SELECT RAISE(ABORT, 'Immunitas-Omega: Ledger UPDATE prohibited'); END;

CREATE TRIGGER IF NOT EXISTS prevent_tx_delete BEFORE DELETE ON transactions
BEGIN SELECT RAISE(ABORT, 'Immunitas-Omega: Ledger DELETE prohibited'); END;
"""

# ─── Heartbeats ───────────────────────────────────────────────────────
CREATE_HEARTBEATS = """
CREATE TABLE IF NOT EXISTS heartbeats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    project     TEXT NOT NULL,
    entity      TEXT,
    category    TEXT NOT NULL,
    branch      TEXT,
    language    TEXT,
    timestamp   TEXT NOT NULL,
    meta        TEXT DEFAULT '{}'
);
"""

CREATE_HEARTBEATS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_hb_tenant ON heartbeats(tenant_id);
CREATE INDEX IF NOT EXISTS idx_hb_project ON heartbeats(project);
CREATE INDEX IF NOT EXISTS idx_hb_timestamp ON heartbeats(timestamp);
CREATE INDEX IF NOT EXISTS idx_hb_category ON heartbeats(category);
"""

# ─── Time Entries ─────────────────────────────────────────────────────
CREATE_TIME_ENTRIES = """
CREATE TABLE IF NOT EXISTS time_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    project     TEXT NOT NULL,
    category    TEXT NOT NULL,
    start_time  TEXT NOT NULL,
    end_time    TEXT NOT NULL,
    duration_s  INTEGER NOT NULL,
    entities    TEXT DEFAULT '[]',
    heartbeats  INTEGER DEFAULT 0,
    meta        TEXT DEFAULT '{}'
);
"""

CREATE_TIME_ENTRIES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_te_tenant ON time_entries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_te_project ON time_entries(project);
CREATE INDEX IF NOT EXISTS idx_te_start ON time_entries(start_time);
"""

# ─── Metadata Table ───────────────────────────────────────────────────
CREATE_META = """
CREATE TABLE IF NOT EXISTS cortex_meta (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""

# ─── Ghosts ───────────────────────────────────────────────────────────
CREATE_GHOSTS = """
CREATE TABLE IF NOT EXISTS ghosts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    reference       TEXT NOT NULL,
    context         TEXT,
    project         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open',
    target_id       INTEGER,
    confidence      REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at     TEXT,
    expires_at      TEXT,
    meta            TEXT DEFAULT '{}'
);
"""

CREATE_GHOSTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ghosts_ref ON ghosts(reference);
"""

# ─── Compactor Logs ───────────────────────────────────────────────────
CREATE_COMPACTION_LOG = """
CREATE TABLE IF NOT EXISTS compaction_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    project         TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    original_ids    TEXT,
    new_fact_id     INTEGER,
    facts_before    INTEGER,
    facts_after     INTEGER,
    timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# ─── Threat Intelligence ──────────────────────────────────────────────
CREATE_THREAT_INTEL = """
CREATE TABLE IF NOT EXISTS threat_intel (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address  TEXT NOT NULL UNIQUE,
    reason      TEXT NOT NULL,
    confidence  TEXT NOT NULL DEFAULT 'C5',
    expires_at  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_THREAT_INTEL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_threat_intel_ip ON threat_intel(ip_address);
"""

# ─── Tenants ──────────────────────────────────────────────────────────
CREATE_TENANTS = """
CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    config      TEXT NOT NULL DEFAULT '{}',
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# ─── Signature Migration ──────────────────────────────────────────────
MIGRATE_ADD_SIGNATURE_COLUMNS = """
ALTER TABLE facts ADD COLUMN signature TEXT;
ALTER TABLE facts ADD COLUMN signer_pubkey TEXT;
"""

# ─── All statements in order ──────────────────────────────────────────
_CORE_SCHEMA = [
    CREATE_FACTS,
    CREATE_FACTS_INDEXES,
    CREATE_EMBEDDINGS,
    CREATE_SPECULAR_EMBEDDINGS,
    CREATE_SESSIONS,
    CREATE_TRANSACTIONS,
    CREATE_TRANSACTIONS_INDEX,
    CREATE_HEARTBEATS,
    CREATE_HEARTBEATS_INDEX,
    CREATE_TIME_ENTRIES,
    CREATE_TIME_ENTRIES_INDEX,
    CREATE_META,
    CREATE_GHOSTS,
    CREATE_GHOSTS_INDEX,
    CREATE_COMPACTION_LOG,
    CREATE_THREAT_INTEL,
    CREATE_THREAT_INTEL_INDEXES,
    CREATE_TENANTS,
]

# Full ordered schema: core + extensions (consensus, episodes, signals, entity_events...)
ALL_SCHEMA = _CORE_SCHEMA + EXTENSION_SCHEMA


# Late import to avoid circular dependency (auth imports from config)
def get_all_schema() -> list[str]:
    """Return ALL_SCHEMA + AUTH_SCHEMA (avoids circular import)."""
    from cortex.auth import AUTH_SCHEMA

    return ALL_SCHEMA + [AUTH_SCHEMA]


def get_init_meta() -> list[tuple[str, str]]:
    """Return initial metadata key-value pairs."""
    return [
        ("schema_version", SCHEMA_VERSION),
        ("engine", "cortex"),
        ("created_by", "cortex-init"),
    ]
