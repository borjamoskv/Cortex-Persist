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
    signature       TEXT NOT NULL CHECK(length(signature) > 0),
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

CREATE_LLM_TELEMETRY = """
CREATE TABLE IF NOT EXISTS llm_telemetry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    intent          TEXT,
    resolved_by     TEXT,
    project         TEXT,
    tier            TEXT NOT NULL,
    depth           INTEGER NOT NULL,
    latency_ms      REAL,
    errors          TEXT DEFAULT '[]',
    timestamp       REAL NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_LLM_TELEMETRY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_llm_telemetry_tier ON llm_telemetry(tier);
CREATE INDEX IF NOT EXISTS idx_llm_telemetry_timestamp ON llm_telemetry(timestamp);
"""


CREATE_LOCK_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_lock_intents_resource ON lock_intents(resource);
CREATE INDEX IF NOT EXISTS idx_lock_intents_agent ON lock_intents(agent_id);
"""

# ─── Full-Text Search (Decoupled in v5) ─────────────────────────────
CREATE_FACTS_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    content,
    project,
    tags,
    fact_type
);
"""

CREATE_FACTS_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS trg_facts_fts_insert
AFTER INSERT ON facts
BEGIN
  INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
  VALUES (NEW.id, NEW.content, NEW.project, NEW.tags, NEW.fact_type);
END;

CREATE TRIGGER IF NOT EXISTS trg_facts_fts_update
AFTER UPDATE OF content, project, tags, fact_type ON facts
BEGIN
  DELETE FROM facts_fts WHERE rowid = OLD.id;
  INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
  VALUES (NEW.id, NEW.content, NEW.project, NEW.tags, NEW.fact_type);
END;

CREATE TRIGGER IF NOT EXISTS trg_facts_fts_delete
BEFORE DELETE ON facts
BEGIN
  DELETE FROM facts_fts WHERE rowid = OLD.id;
END;
"""

# ─── Immutable Ledger (Merkle) ──────────────────────────────────────
CREATE_MERKLE_ROOTS = """
CREATE TABLE IF NOT EXISTS merkle_roots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    root_hash       TEXT NOT NULL,
    tx_start_id     INTEGER NOT NULL,
    tx_end_id       INTEGER NOT NULL,
    tx_count        INTEGER NOT NULL,
    timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# ─── Procedural Engrams (Ω₃ Immutability) ─────────────────────────────
CREATE_PROCEDURAL_ENGRAMS = """
CREATE TABLE IF NOT EXISTS procedural_engrams (
    skill_name      TEXT PRIMARY KEY,
    invocations     INTEGER NOT NULL DEFAULT 0,
    success_rate    REAL NOT NULL DEFAULT 1.0,
    avg_latency_ms  REAL NOT NULL DEFAULT 0.0,
    last_invoked    REAL NOT NULL,
    permanent       INTEGER NOT NULL DEFAULT 0
);

CREATE TRIGGER IF NOT EXISTS trg_procedural_engrams_permanent_immutability
BEFORE UPDATE OF permanent ON procedural_engrams
FOR EACH ROW
WHEN OLD.permanent = 1 AND NEW.permanent = 0
BEGIN
    SELECT RAISE(ABORT, 'Immunitas-Omega (Ω3): Unidirectional immutability violated. Cannot revert permanent=1 to permanent=0');
END;
"""

# ── Lock TTL Enforcement (Ω₃ -- dead agents cannot hold locks forever) ──
CREATE_LOCK_TTL_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS trg_lock_ttl_release
AFTER INSERT ON lock_intents
BEGIN
    UPDATE lock_state
    SET holder_agent = NULL, acquired_at = NULL,
        expires_at = NULL, queue_depth = MAX(0, queue_depth - 1)
    WHERE expires_at IS NOT NULL AND expires_at < datetime('now');
END;
"""

CREATE_CAUSAL_EDGES = """
CREATE TABLE IF NOT EXISTS causal_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id         INTEGER NOT NULL,
    parent_id       INTEGER,
    signal_id       INTEGER,
    edge_type       TEXT NOT NULL DEFAULT 'triggered_by',
    project         TEXT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (fact_id) REFERENCES facts(id)
);
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
    CREATE_LOCK_TTL_TRIGGER,
    CREATE_LLM_TELEMETRY,
    CREATE_LLM_TELEMETRY_INDEX,
    CREATE_CAUSAL_EDGES,
    CREATE_PROCEDURAL_ENGRAMS,
    CREATE_FACTS_FTS,
    CREATE_FACTS_FTS_TRIGGERS,
    CREATE_MERKLE_ROOTS,
]
