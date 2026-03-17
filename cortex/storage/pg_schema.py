"""
CORTEX v6.0 — PostgreSQL Schema Definitions.

Translated from SQLite schema.py for PostgreSQL/AlloyDB compatibility.
Key differences:
- SERIAL/BIGSERIAL instead of INTEGER PRIMARY KEY AUTOINCREMENT
- NOW() instead of datetime('now')
- No VIRTUAL TABLE (FTS5/vec0) — use pgvector + pg_trgm instead
- BOOLEAN instead of INTEGER for boolean fields
- TEXT[] or JSONB instead of TEXT for structured fields
"""

from __future__ import annotations

__all__ = [
    "PG_ALL_SCHEMA",
    "PG_EXTENSIONS",
    "PG_SCHEMA_VERSION",
]

PG_SCHEMA_VERSION = "6.0.0"

# ─── Required Extensions ────────────────────────────────────────────
PG_EXTENSIONS = """
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;
"""

# ─── Core Facts Table ────────────────────────────────────────────────
PG_CREATE_FACTS = """
CREATE TABLE IF NOT EXISTS facts (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    project         TEXT NOT NULL,
    content         TEXT NOT NULL,
    fact_type       TEXT NOT NULL DEFAULT 'knowledge',
    tags            TEXT NOT NULL DEFAULT '[]',
    confidence      TEXT NOT NULL DEFAULT 'stated',
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until     TIMESTAMPTZ,
    source          TEXT,
    meta            JSONB DEFAULT '{}',
    consensus_score DOUBLE PRECISION DEFAULT 1.0,
    hash            TEXT,
    signature       TEXT,
    signer_pubkey   TEXT,
    is_quarantined  BOOLEAN NOT NULL DEFAULT FALSE,
    quarantined_at  TIMESTAMPTZ,
    quarantine_reason TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tx_id           BIGINT REFERENCES transactions(id),
    is_tombstoned   BOOLEAN NOT NULL DEFAULT FALSE,
    tombstoned_at   TIMESTAMPTZ,
    embedding       vector(384)
);
"""

PG_CREATE_FACTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_facts_tenant ON facts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_facts_project ON facts(project);
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_proj_type ON facts(project, fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_valid ON facts(valid_from, valid_until);
CREATE INDEX IF NOT EXISTS idx_facts_confidence ON facts(confidence);
CREATE INDEX IF NOT EXISTS idx_facts_quarantine ON facts(is_quarantined);
CREATE INDEX IF NOT EXISTS idx_facts_tombstone ON facts(is_tombstoned);
CREATE INDEX IF NOT EXISTS idx_facts_content_trgm ON facts USING gin(content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_facts_embedding
    ON facts USING ivfflat(embedding vector_cosine_ops)
    WITH (lists = 100);
"""

# ─── Sessions Log ────────────────────────────────────────────────────
PG_CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    date            TEXT NOT NULL,
    focus           JSONB NOT NULL DEFAULT '[]',
    summary         TEXT NOT NULL,
    conversations   INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# ─── Transaction Ledger (append-only, hash-chained) ──────────────────
PG_CREATE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    project     TEXT NOT NULL,
    action      TEXT NOT NULL,
    detail      TEXT,
    prev_hash   TEXT,
    hash        TEXT NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

PG_CREATE_TRANSACTIONS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_tx_tenant ON transactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tx_project ON transactions(project);
CREATE INDEX IF NOT EXISTS idx_tx_action ON transactions(action);
"""

# ─── Heartbeats ──────────────────────────────────────────────────────
PG_CREATE_HEARTBEATS = """
CREATE TABLE IF NOT EXISTS heartbeats (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    project     TEXT NOT NULL,
    entity      TEXT,
    category    TEXT NOT NULL,
    branch      TEXT,
    language    TEXT,
    timestamp   TIMESTAMPTZ NOT NULL,
    meta        JSONB DEFAULT '{}'
);
"""

PG_CREATE_HEARTBEATS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_hb_tenant ON heartbeats(tenant_id);
CREATE INDEX IF NOT EXISTS idx_hb_project ON heartbeats(project);
CREATE INDEX IF NOT EXISTS idx_hb_timestamp ON heartbeats(timestamp);
CREATE INDEX IF NOT EXISTS idx_hb_category ON heartbeats(category);
"""

# ─── Time Entries ────────────────────────────────────────────────────
PG_CREATE_TIME_ENTRIES = """
CREATE TABLE IF NOT EXISTS time_entries (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    project     TEXT NOT NULL,
    category    TEXT NOT NULL,
    start_time  TIMESTAMPTZ NOT NULL,
    end_time    TIMESTAMPTZ NOT NULL,
    duration_s  INTEGER NOT NULL,
    entities    JSONB DEFAULT '[]',
    heartbeats  INTEGER DEFAULT 0,
    meta        JSONB DEFAULT '{}'
);
"""

PG_CREATE_TIME_ENTRIES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_te_tenant ON time_entries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_te_project ON time_entries(project);
CREATE INDEX IF NOT EXISTS idx_te_start ON time_entries(start_time);
"""

# ─── Metadata Table ──────────────────────────────────────────────────
PG_CREATE_META = """
CREATE TABLE IF NOT EXISTS cortex_meta (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""

# ─── Consensus Votes ─────────────────────────────────────────────────
PG_CREATE_VOTES = """
CREATE TABLE IF NOT EXISTS consensus_votes (
    id      BIGSERIAL PRIMARY KEY,
    fact_id BIGINT NOT NULL REFERENCES facts(id),
    agent   TEXT NOT NULL,
    vote    INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(fact_id, agent)
);
"""

# ─── Agents ──────────────────────────────────────────────────────────
PG_CREATE_AGENTS = """
CREATE TABLE IF NOT EXISTS agents (
    id                  TEXT PRIMARY KEY,
    public_key          TEXT NOT NULL,
    name                TEXT NOT NULL,
    agent_type          TEXT NOT NULL DEFAULT 'ai',
    tenant_id           TEXT NOT NULL DEFAULT 'default',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reputation_score    DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    reputation_stake    DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_votes         INTEGER DEFAULT 0,
    successful_votes    INTEGER DEFAULT 0,
    disputed_votes      INTEGER DEFAULT 0,
    last_active_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active           BOOLEAN DEFAULT TRUE,
    is_verified         BOOLEAN DEFAULT FALSE,
    meta                JSONB DEFAULT '{}'
);
"""

# ─── Votes V2 ────────────────────────────────────────────────────────
PG_CREATE_VOTES_V2 = """
CREATE TABLE IF NOT EXISTS consensus_votes_v2 (
    id              BIGSERIAL PRIMARY KEY,
    fact_id         BIGINT NOT NULL REFERENCES facts(id),
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    vote            INTEGER NOT NULL,
    vote_weight     DOUBLE PRECISION NOT NULL,
    agent_rep_at_vote DOUBLE PRECISION NOT NULL,
    stake_at_vote   DOUBLE PRECISION DEFAULT 0.0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decay_factor    DOUBLE PRECISION DEFAULT 1.0,
    vote_reason     TEXT,
    meta            JSONB DEFAULT '{}',
    UNIQUE(fact_id, agent_id)
);
"""

# ─── Trust Edges ──────────────────────────────────────────────────────
PG_CREATE_TRUST_EDGES = """
CREATE TABLE IF NOT EXISTS trust_edges (
    id              BIGSERIAL PRIMARY KEY,
    source_agent    TEXT NOT NULL REFERENCES agents(id),
    target_agent    TEXT NOT NULL REFERENCES agents(id),
    trust_weight    DOUBLE PRECISION NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source_agent, target_agent)
);
"""

# ─── Consensus Outcomes ──────────────────────────────────────────────
PG_CREATE_OUTCOMES = """
CREATE TABLE IF NOT EXISTS consensus_outcomes (
    id                  BIGSERIAL PRIMARY KEY,
    fact_id             BIGINT NOT NULL REFERENCES facts(id),
    final_state         TEXT NOT NULL,
    final_score         DOUBLE PRECISION NOT NULL,
    resolved_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_votes         INTEGER NOT NULL,
    unique_agents       INTEGER NOT NULL,
    reputation_sum      DOUBLE PRECISION NOT NULL,
    resolution_method   TEXT DEFAULT 'reputation_weighted',
    meta                JSONB DEFAULT '{}'
);
"""

PG_CREATE_RWC_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_agents_reputation ON agents(reputation_score DESC);
CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active, last_active_at);
CREATE INDEX IF NOT EXISTS idx_votes_v2_fact ON consensus_votes_v2(fact_id);
CREATE INDEX IF NOT EXISTS idx_votes_v2_agent ON consensus_votes_v2(agent_id);
CREATE INDEX IF NOT EXISTS idx_trust_source ON trust_edges(source_agent);
CREATE INDEX IF NOT EXISTS idx_trust_target ON trust_edges(target_agent);
"""

# ─── Ghosts ──────────────────────────────────────────────────────────
PG_CREATE_GHOSTS = """
CREATE TABLE IF NOT EXISTS ghosts (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    reference       TEXT NOT NULL,
    context         TEXT,
    project         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open',
    target_id       BIGINT,
    confidence      DOUBLE PRECISION DEFAULT 0.0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    meta            JSONB DEFAULT '{}'
);
"""

PG_CREATE_GHOSTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ghosts_ref ON ghosts(reference);
"""

# ─── Compaction Log ──────────────────────────────────────────────────
PG_CREATE_COMPACTION_LOG = """
CREATE TABLE IF NOT EXISTS compaction_log (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    project         TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    original_ids    JSONB,
    new_fact_id     BIGINT,
    facts_before    INTEGER,
    facts_after     INTEGER,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# ─── Context Snapshots ───────────────────────────────────────────────
PG_CREATE_CONTEXT_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS context_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    active_project  TEXT,
    confidence      TEXT NOT NULL,
    signals_used    INTEGER NOT NULL,
    summary         TEXT NOT NULL,
    signals_json    JSONB,
    projects_json   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

PG_CREATE_CONTEXT_SNAPSHOTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ctx_snap_project ON context_snapshots(active_project);
CREATE INDEX IF NOT EXISTS idx_ctx_snap_created ON context_snapshots(created_at);
"""

# ─── Episodes ────────────────────────────────────────────────────────
PG_CREATE_EPISODES = """
CREATE TABLE IF NOT EXISTS episodes (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    session_id  TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    content     TEXT NOT NULL,
    project     TEXT,
    emotion     TEXT DEFAULT 'neutral',
    tags        JSONB DEFAULT '[]',
    meta        JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

PG_CREATE_EPISODES_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ep_tenant ON episodes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ep_session ON episodes(session_id);
CREATE INDEX IF NOT EXISTS idx_ep_project_type ON episodes(project, event_type);
CREATE INDEX IF NOT EXISTS idx_ep_created ON episodes(created_at);
CREATE INDEX IF NOT EXISTS idx_ep_event_type ON episodes(event_type);
CREATE INDEX IF NOT EXISTS idx_ep_content_trgm ON episodes USING gin(content gin_trgm_ops);
"""

# ─── Threat Intelligence ─────────────────────────────────────────────
PG_CREATE_THREAT_INTEL = """
CREATE TABLE IF NOT EXISTS threat_intel (
    id          BIGSERIAL PRIMARY KEY,
    ip_address  TEXT NOT NULL UNIQUE,
    reason      TEXT NOT NULL,
    confidence  TEXT NOT NULL DEFAULT 'C5',
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

PG_CREATE_THREAT_INTEL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_threat_intel_ip ON threat_intel(ip_address);
"""

# ─── Tenants ─────────────────────────────────────────────────────────
PG_CREATE_TENANTS = """
CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    config      JSONB NOT NULL DEFAULT '{}',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# ─── Evolution State ─────────────────────────────────────────────────
PG_CREATE_EVOLUTION_STATE = """
CREATE TABLE IF NOT EXISTS evolution_state (
    id          BIGSERIAL PRIMARY KEY,
    cycle       INTEGER NOT NULL,
    agent_domain TEXT NOT NULL,
    agent_json  JSONB NOT NULL,
    saved_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

PG_CREATE_EVOLUTION_STATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_evo_cycle ON evolution_state(cycle);
CREATE INDEX IF NOT EXISTS idx_evo_domain ON evolution_state(agent_domain);
"""

# ─── Signal Bus ──────────────────────────────────────────────────────
PG_CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id          BIGSERIAL PRIMARY KEY,
    event_type  TEXT NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}',
    source      TEXT NOT NULL,
    project     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consumed_by JSONB NOT NULL DEFAULT '[]'
);
"""

PG_CREATE_SIGNALS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(event_type);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_project ON signals(project);
"""

# ─── Entity Events (Solid-State Substrate) ───────────────────────────
PG_CREATE_ENTITY_EVENTS = """
CREATE TABLE IF NOT EXISTS entity_events (
    id              TEXT PRIMARY KEY,
    entity_id       BIGINT NOT NULL,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    event_type      TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}',
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    prev_hash       TEXT NOT NULL DEFAULT 'GENESIS',
    signature       TEXT NOT NULL,
    signer          TEXT NOT NULL DEFAULT '',
    schema_version  TEXT NOT NULL DEFAULT '1'
);
"""

PG_CREATE_ENTITY_EVENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ee_entity ON entity_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_ee_tenant ON entity_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ee_type ON entity_events(event_type);
CREATE INDEX IF NOT EXISTS idx_ee_timestamp ON entity_events(timestamp);
"""

# ─── All statements in order ─────────────────────────────────────────
# Note: transactions table must come before facts (FK reference)
PG_ALL_SCHEMA = [
    PG_CREATE_TRANSACTIONS,
    PG_CREATE_TRANSACTIONS_INDEX,
    PG_CREATE_FACTS,
    PG_CREATE_FACTS_INDEXES,
    PG_CREATE_SESSIONS,
    PG_CREATE_HEARTBEATS,
    PG_CREATE_HEARTBEATS_INDEX,
    PG_CREATE_TIME_ENTRIES,
    PG_CREATE_TIME_ENTRIES_INDEX,
    PG_CREATE_META,
    PG_CREATE_VOTES,
    PG_CREATE_AGENTS,
    PG_CREATE_VOTES_V2,
    PG_CREATE_TRUST_EDGES,
    PG_CREATE_OUTCOMES,
    PG_CREATE_RWC_INDEXES,
    PG_CREATE_GHOSTS,
    PG_CREATE_GHOSTS_INDEX,
    PG_CREATE_COMPACTION_LOG,
    PG_CREATE_CONTEXT_SNAPSHOTS,
    PG_CREATE_CONTEXT_SNAPSHOTS_INDEX,
    PG_CREATE_EPISODES,
    PG_CREATE_EPISODES_INDEXES,
    PG_CREATE_THREAT_INTEL,
    PG_CREATE_THREAT_INTEL_INDEXES,
    PG_CREATE_TENANTS,
    PG_CREATE_EVOLUTION_STATE,
    PG_CREATE_EVOLUTION_STATE_INDEX,
    PG_CREATE_SIGNALS,
    PG_CREATE_SIGNALS_INDEXES,
    PG_CREATE_ENTITY_EVENTS,
    PG_CREATE_ENTITY_EVENTS_INDEXES,
]
