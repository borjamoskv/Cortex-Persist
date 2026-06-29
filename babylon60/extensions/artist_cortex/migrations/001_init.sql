PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- =========================
-- CORE
-- =========================

CREATE TABLE IF NOT EXISTS cortex_sessions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at      TEXT NOT NULL DEFAULT (datetime('now')),
  ended_at        TEXT,
  operator_id     TEXT,
  core_vector     TEXT NOT NULL CHECK (core_vector IN ('ARTE_PURO','RECONOCIMIENTO_LIQUIDO','PROTECCION_DE_IDENTIDAD')),
  notes           TEXT
);

CREATE TABLE IF NOT EXISTS cortex_artifacts (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id      INTEGER NOT NULL REFERENCES cortex_sessions(id) ON DELETE CASCADE,
  artifact_key    TEXT NOT NULL UNIQUE,
  artifact_type   TEXT NOT NULL,              -- music | visual | prompt | code | narrative | other
  title           TEXT,
  source          TEXT,                       -- raw input / prompt / commit hash / file path
  content         TEXT,                       -- canonical text payload
  status          TEXT NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft','review','accepted','rejected','archived')),
  originality_raw REAL NOT NULL DEFAULT 0.0 CHECK (originality_raw BETWEEN 0 AND 1),
  recombination   REAL NOT NULL DEFAULT 0.0 CHECK (recombination BETWEEN 0 AND 1),
  friction_ms     INTEGER NOT NULL DEFAULT 0,
  attention_yield REAL NOT NULL DEFAULT 0.0,
  aesthetic_hash  TEXT,                       -- stable 3-vector encoded as string / json
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cortex_artifacts_session
  ON cortex_artifacts(session_id);

CREATE INDEX IF NOT EXISTS idx_cortex_artifacts_status
  ON cortex_artifacts(status);

-- =========================
-- TELEMETRY
-- =========================

CREATE TABLE IF NOT EXISTS cortex_events (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id      INTEGER REFERENCES cortex_sessions(id) ON DELETE CASCADE,
  artifact_id     INTEGER REFERENCES cortex_artifacts(id) ON DELETE CASCADE,
  event_type      TEXT NOT NULL,               -- think | commit | render | reject | delegate | hash | feedback
  t0_ms           INTEGER,
  t1_ms           INTEGER,
  delta_ms        INTEGER GENERATED ALWAYS AS (
                    CASE
                      WHEN t0_ms IS NOT NULL AND t1_ms IS NOT NULL THEN t1_ms - t0_ms
                      ELSE NULL
                    END
                  ) VIRTUAL,
  payload         TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cortex_events_artifact
  ON cortex_events(artifact_id);

-- =========================
-- EVALUATION
-- =========================

CREATE TABLE IF NOT EXISTS cortex_metrics (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  artifact_id     INTEGER NOT NULL REFERENCES cortex_artifacts(id) ON DELETE CASCADE,
  metric_name     TEXT NOT NULL,               -- originality | friction | attention | coherence | novelty | distribution
  metric_value    REAL NOT NULL,
  metric_target   REAL,
  metric_threshold REAL,
  verdict         TEXT NOT NULL DEFAULT 'pending'
                  CHECK (verdict IN ('pending','pass','warn','fail')),
  rationale       TEXT,
  measured_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cortex_metrics_artifact
  ON cortex_metrics(artifact_id);

CREATE INDEX IF NOT EXISTS idx_cortex_metrics_name
  ON cortex_metrics(metric_name);

-- =========================
-- AESTHETIC ANCHORS
-- =========================

CREATE TABLE IF NOT EXISTS cortex_anchors (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  anchor_key      TEXT NOT NULL UNIQUE,        -- refs, palettes, motifs, sonic signatures
  anchor_type     TEXT NOT NULL,               -- visual | sonic | verbal | structural
  anchor_value    TEXT NOT NULL,
  locked          INTEGER NOT NULL DEFAULT 0 CHECK (locked IN (0,1)),
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =========================
-- DELEGATION / AGENTS
-- =========================

CREATE TABLE IF NOT EXISTS cortex_agents (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_key       TEXT NOT NULL UNIQUE,        -- generator | critic | assembler | noise_injector
  role            TEXT NOT NULL,
  config_json     TEXT NOT NULL DEFAULT '{}',
  active          INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cortex_agent_runs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id      INTEGER NOT NULL REFERENCES cortex_sessions(id) ON DELETE CASCADE,
  artifact_id     INTEGER REFERENCES cortex_artifacts(id) ON DELETE CASCADE,
  agent_id        INTEGER NOT NULL REFERENCES cortex_agents(id) ON DELETE CASCADE,
  input_hash      TEXT,
  output_hash     TEXT,
  score           REAL,
  notes           TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cortex_agent_runs_session
  ON cortex_agent_runs(session_id);

-- =========================
-- VECTOR STORE
-- =========================

CREATE VIRTUAL TABLE IF NOT EXISTS cortex_embeddings
USING vec0(embedding float[1536]);

CREATE TABLE IF NOT EXISTS cortex_embedding_map (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  artifact_id     INTEGER NOT NULL UNIQUE REFERENCES cortex_artifacts(id) ON DELETE CASCADE,
  embedding_key   TEXT NOT NULL UNIQUE,
  model_name      TEXT NOT NULL,
  dims            INTEGER NOT NULL DEFAULT 1536,
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
