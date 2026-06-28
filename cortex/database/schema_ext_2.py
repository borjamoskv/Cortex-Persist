# ─── Signal Bus (L1 Consciousness - Cross-Tool Reactive Signaling) ───
CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
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

# ─── Entity Events (Solid-State Substrate - Append-Only Ledger) ──────
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

# ─── Execution Trace Ledger (Memory Thermodynamics Graph) ─────────────
CREATE_EXECUTION_TRACE_LEDGER = """
CREATE TABLE IF NOT EXISTS execution_trace_ledger (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    origin          TEXT NOT NULL,
    cost            REAL NOT NULL,
    lineage         TEXT NOT NULL DEFAULT '[]',
    outcome         TEXT NOT NULL,
    rollback_possible BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_exec_trace_tenant ON execution_trace_ledger(tenant_id);
CREATE INDEX IF NOT EXISTS idx_exec_trace_outcome ON execution_trace_ledger(outcome);
"""

# ─── Sovereign Locks (Axiom Ω₂ - Lock-Free Concurrency) ──────────────
CREATE_LOCK_INTENTS = """
CREATE TABLE IF NOT EXISTS lock_intents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
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
    tenant_id       TEXT NOT NULL DEFAULT 'default',
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
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
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

# ─── Enrichment Queue (P0 Decoupling) ───────────────────────────────
CREATE_ENRICHMENT_JOBS = """
CREATE TABLE IF NOT EXISTS enrichment_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT UNIQUE,
    event_id        TEXT,
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    job_type        TEXT NOT NULL DEFAULT 'embedding',
    status          TEXT NOT NULL DEFAULT 'queued',
    priority        INTEGER DEFAULT 0,
    attempts        INTEGER DEFAULT 0,
    last_error      TEXT,
    next_attempt_ts TEXT,
    next_attempt_at TEXT,
    payload         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(event_id) REFERENCES entity_events(id) ON DELETE CASCADE
);
"""

CREATE_ENRICHMENT_JOBS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_enrichment_jobs_status ON enrichment_jobs(status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_enrichment_jobs_fact ON enrichment_jobs(fact_id);
"""

# ─── Full-Text Search (Decoupled in v5) ─────────────────────────────
CREATE_FACTS_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    content,
    project,
    tags,
    fact_type,
    tenant_id UNINDEXED
);
"""

# ─── Immutable Ledger (Merkle) ──────────────────────────────────────
CREATE_MERKLE_ROOTS = """
CREATE TABLE IF NOT EXISTS merkle_roots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT '__global__',
    root_hash       TEXT NOT NULL,
    tx_start_id     INTEGER NOT NULL,
    tx_end_id       INTEGER NOT NULL,
    tx_count        INTEGER NOT NULL,
    timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_INTEGRITY_CHECKS = """
CREATE TABLE IF NOT EXISTS integrity_checks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type      TEXT NOT NULL,
    status          TEXT NOT NULL,
    details         TEXT,
    started_at      TEXT NOT NULL,
    completed_at    TEXT NOT NULL
);
"""

CREATE_AUDIT_EXPORTS = """
CREATE TABLE IF NOT EXISTS audit_exports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    export_type     TEXT NOT NULL,
    filename        TEXT NOT NULL,
    file_hash       TEXT NOT NULL,
    tx_start_id     INTEGER NOT NULL,
    tx_end_id       INTEGER NOT NULL,
    exported_at     TEXT NOT NULL DEFAULT (datetime('now')),
    exported_by     TEXT NOT NULL
);
"""

# ─── Procedural Engrams (Ω₃ Immutability) ─────────────────────────────
CREATE_PROCEDURAL_ENGRAMS = """
CREATE TABLE IF NOT EXISTS procedural_engrams (
    skill_name      TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
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
    fact_hash       TEXT UNIQUE,
    fact_id         INTEGER NOT NULL,
    parent_id       INTEGER,
    signal_id       INTEGER,
    edge_type       TEXT NOT NULL DEFAULT 'triggered_by',
    confidence      REAL DEFAULT 1.0,
    agent_id        TEXT,
    project         TEXT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (fact_id) REFERENCES facts(id)
);
"""

CREATE_EPISODES_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS trg_episodes_ai AFTER INSERT ON episodes BEGIN
  INSERT INTO episodes_fts(rowid, content, event_type, project, tenant_id)
  VALUES (new.id, new.content, new.event_type, new.project, new.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_episodes_ad AFTER DELETE ON episodes BEGIN
  INSERT INTO episodes_fts(episodes_fts, rowid, content, event_type, project, tenant_id)
  VALUES ('delete', old.id, old.content, old.event_type, old.project, old.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_episodes_au AFTER UPDATE ON episodes BEGIN
  INSERT INTO episodes_fts(episodes_fts, rowid, content, event_type, project, tenant_id)
  VALUES ('delete', old.id, old.content, old.event_type, old.project, old.tenant_id);
  INSERT INTO episodes_fts(rowid, content, event_type, project, tenant_id)
  VALUES (new.id, new.content, new.event_type, new.project, new.tenant_id);
END;
"""

CREATE_FACTS_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS trg_facts_ai AFTER INSERT ON facts BEGIN
  INSERT INTO facts_fts(rowid, content, project, tags, fact_type, tenant_id)
  VALUES (new.id, new.content, new.project, new.tags, new.fact_type, new.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_facts_ad AFTER DELETE ON facts BEGIN
  DELETE FROM facts_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_facts_au AFTER UPDATE ON facts BEGIN
  DELETE FROM facts_fts WHERE rowid = old.id;
  INSERT INTO facts_fts(rowid, content, project, tags, fact_type, tenant_id)
  VALUES (new.id, new.content, new.project, new.tags, new.fact_type, new.tenant_id);
END;
"""

# Convenience export - all extension statements in insertion order
