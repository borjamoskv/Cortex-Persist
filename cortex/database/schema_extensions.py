"""schema_extensions — Extended SQLite tables for CORTEX v5.

Extracted from database/schema.py to satisfy the Landauer LOC barrier.
Contains: Consensus/RWC (votes, agents, trust), Monitoring (signals, entity_events),
Analytics (evolution_state, episodes, episodes_fts, context_snapshots, episodes_indexes).

Import from schema.py via `from cortex.database.schema_extensions import *`.
"""

from __future__ import annotations

# ─── Consensus Votes (Neural Swarm Consensus) ───────────────────────
CREATE_VOTES = """
CREATE TABLE IF NOT EXISTS consensus_votes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id INTEGER NOT NULL REFERENCES facts(id),
    agent   TEXT NOT NULL,
    vote    INTEGER NOT NULL, -- 1 (verify), -1 (dispute)
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(fact_id, agent)
);
"""

# ─── Reputation-Weighted Consensus (v2) ─────────────────────────────
CREATE_AGENTS = """
CREATE TABLE IF NOT EXISTS agents (
    id              TEXT PRIMARY KEY,
    public_key      TEXT NOT NULL,
    name            TEXT NOT NULL,
    agent_type      TEXT NOT NULL DEFAULT 'ai',
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    reputation_score    REAL NOT NULL DEFAULT 0.5,
    reputation_stake    REAL NOT NULL DEFAULT 0.0,
    total_votes         INTEGER DEFAULT 0,
    successful_votes    INTEGER DEFAULT 0,
    disputed_votes      INTEGER DEFAULT 0,
    last_active_at      TEXT NOT NULL DEFAULT (datetime('now')),
    is_active           BOOLEAN DEFAULT TRUE,
    is_verified         BOOLEAN DEFAULT FALSE,
    meta                TEXT DEFAULT '{}'
);
"""

CREATE_VOTES_V2 = """
CREATE TABLE IF NOT EXISTS consensus_votes_v2 (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    vote            INTEGER NOT NULL,
    vote_weight     REAL NOT NULL,
    agent_rep_at_vote   REAL NOT NULL,
    stake_at_vote       REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    decay_factor    REAL DEFAULT 1.0,
    vote_reason     TEXT,
    meta            TEXT DEFAULT '{}',
    UNIQUE(fact_id, agent_id)
);
"""

CREATE_TRUST_EDGES = """
CREATE TABLE IF NOT EXISTS trust_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_agent    TEXT NOT NULL REFERENCES agents(id),
    target_agent    TEXT NOT NULL REFERENCES agents(id),
    trust_weight    REAL NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_agent, target_agent)
);
"""

CREATE_OUTCOMES = """
CREATE TABLE IF NOT EXISTS consensus_outcomes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    final_state     TEXT NOT NULL,
    final_score     REAL NOT NULL,
    resolved_at     TEXT NOT NULL DEFAULT (datetime('now')),
    total_votes     INTEGER NOT NULL,
    unique_agents   INTEGER NOT NULL,
    reputation_sum  REAL NOT NULL,
    resolution_method   TEXT DEFAULT 'reputation_weighted',
    meta                TEXT DEFAULT '{}'
);
"""

CREATE_RWC_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_agents_reputation ON agents(reputation_score DESC);
CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active, last_active_at);
CREATE INDEX IF NOT EXISTS idx_votes_v2_fact ON consensus_votes_v2(fact_id);
CREATE INDEX IF NOT EXISTS idx_votes_v2_agent ON consensus_votes_v2(agent_id);
CREATE INDEX IF NOT EXISTS idx_trust_source ON trust_edges(source_agent);
CREATE INDEX IF NOT EXISTS idx_trust_target ON trust_edges(target_agent);
"""

# ─── Context Snapshots (Ambient Intelligence) ────────────────────────
CREATE_CONTEXT_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS context_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    active_project  TEXT,
    confidence      TEXT NOT NULL,
    signals_used    INTEGER NOT NULL,
    summary         TEXT NOT NULL,
    signals_json    TEXT,
    projects_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_CONTEXT_SNAPSHOTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ctx_snap_project ON context_snapshots(active_project);
CREATE INDEX IF NOT EXISTS idx_ctx_snap_created ON context_snapshots(created_at);
"""

# ─── Episodic Memory (Native Persistent Memory) ─────────────────────
CREATE_EPISODES = """
CREATE TABLE IF NOT EXISTS episodes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    session_id  TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    content     TEXT NOT NULL,
    project     TEXT,
    emotion     TEXT DEFAULT 'neutral',
    tags        TEXT DEFAULT '[]',
    meta        TEXT DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_EPISODES_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ep_tenant ON episodes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ep_session ON episodes(session_id);
CREATE INDEX IF NOT EXISTS idx_ep_project_type ON episodes(project, event_type);
CREATE INDEX IF NOT EXISTS idx_ep_created ON episodes(created_at);
CREATE INDEX IF NOT EXISTS idx_ep_event_type ON episodes(event_type);
"""

CREATE_EPISODES_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
    content,
    event_type,
    project,
    content='episodes',
    content_rowid='id'
);
"""

# ─── Evolution State (Continuous Improvement Engine) ─────────────────
CREATE_EVOLUTION_STATE = """
CREATE TABLE IF NOT EXISTS evolution_state (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle       INTEGER NOT NULL,
    agent_domain TEXT NOT NULL,
    agent_json  TEXT NOT NULL,
    saved_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_EVOLUTION_STATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_evo_cycle ON evolution_state(cycle);
CREATE INDEX IF NOT EXISTS idx_evo_domain ON evolution_state(agent_domain);
"""

# ─── Signal Bus (L1 Consciousness — Cross-Tool Reactive Signaling) ───
CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    source      TEXT NOT NULL,
    project     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    consumed_by TEXT NOT NULL DEFAULT '[]'
);
"""

CREATE_SIGNALS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(event_type);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_project ON signals(project);
"""

# ─── Entity Events (Solid-State Substrate — Append-Only Ledger) ──────
CREATE_ENTITY_EVENTS = """
CREATE TABLE IF NOT EXISTS entity_events (
    id              TEXT PRIMARY KEY,
    entity_id       INTEGER NOT NULL,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    event_type      TEXT NOT NULL,
    payload         TEXT NOT NULL DEFAULT '{}',
    timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
    prev_hash       TEXT NOT NULL DEFAULT 'GENESIS',
    signature       TEXT NOT NULL,
    signer          TEXT NOT NULL DEFAULT '',
    schema_version  TEXT NOT NULL DEFAULT '1'
);
"""

CREATE_ENTITY_EVENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ee_entity ON entity_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_ee_tenant ON entity_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ee_type ON entity_events(event_type);
CREATE INDEX IF NOT EXISTS idx_ee_timestamp ON entity_events(timestamp);
"""

# ─── Sovereign Locks (Axiom Ω₂ — Lock-Free Concurrency) ──────────────
CREATE_LOCK_INTENTS = """
CREATE TABLE IF NOT EXISTS lock_intents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    resource        TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    action          TEXT NOT NULL, -- 'request', 'release'
    priority        INTEGER DEFAULT 0,
    timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT
);
"""

CREATE_LOCK_STATE = """
CREATE TABLE IF NOT EXISTS lock_state (
    resource        TEXT PRIMARY KEY,
    holder_agent    TEXT,
    acquired_at     TEXT,
    expires_at      TEXT,
    queue_depth     INTEGER DEFAULT 0
);
"""

CREATE_LOCK_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_lock_intents_resource ON lock_intents(resource);
CREATE INDEX IF NOT EXISTS idx_lock_intents_agent ON lock_intents(agent_id);
"""

# Convenience export — all extension statements in insertion order
EXTENSION_SCHEMA = [
    CREATE_VOTES,
    CREATE_AGENTS,
    CREATE_VOTES_V2,
    CREATE_TRUST_EDGES,
    CREATE_OUTCOMES,
    CREATE_RWC_INDEXES,
    CREATE_CONTEXT_SNAPSHOTS,
    CREATE_CONTEXT_SNAPSHOTS_INDEX,
    CREATE_EPISODES,
    CREATE_EPISODES_INDEXES,
    CREATE_EPISODES_FTS,
    CREATE_EVOLUTION_STATE,
    CREATE_EVOLUTION_STATE_INDEX,
    CREATE_SIGNALS,
    CREATE_SIGNALS_INDEXES,
    CREATE_ENTITY_EVENTS,
    CREATE_ENTITY_EVENTS_INDEXES,
    CREATE_LOCK_INTENTS,
    CREATE_LOCK_STATE,
    CREATE_LOCK_INDEXES,
]
