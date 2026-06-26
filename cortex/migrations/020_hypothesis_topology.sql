-- [C5-REAL] Exergy-Maximized
-- Migration 020: v19 Dependency Graph Fitness & Structural Compression

-- Initialize graph version
INSERT OR IGNORE INTO cortex_meta (key, value) VALUES ('hypothesis_graph_version', '1');

CREATE TABLE IF NOT EXISTS system_hypotheses (
    id UUID PRIMARY KEY,
    fact_id INTEGER, -- Optional linkage to facts table
    statement TEXT NOT NULL,
    probability FLOAT NOT NULL DEFAULT 0.5, -- Pi
    svi FLOAT NOT NULL DEFAULT 1.0, -- Uncertainty
    evi FLOAT NOT NULL DEFAULT 0.0,
    cost FLOAT NOT NULL DEFAULT 1.0, -- Cost (computational, token, api)
    impact FLOAT NOT NULL DEFAULT 1.0, -- Local Impact
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INVALIDATED, SUPERSEDED, ARCHIVED, FALSIFIED
    resolution_reason TEXT, -- e.g., 'parent_false'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(fact_id) REFERENCES facts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS hypothesis_edges (
    parent_id UUID NOT NULL,
    child_id UUID NOT NULL,
    edge_weight REAL NOT NULL DEFAULT 1.0,
    relation_type TEXT NOT NULL DEFAULT 'requires',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY(parent_id, child_id),
    FOREIGN KEY(parent_id) REFERENCES system_hypotheses(id) ON DELETE CASCADE,
    FOREIGN KEY(child_id) REFERENCES system_hypotheses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hypo_edges_parent ON hypothesis_edges(parent_id);
CREATE INDEX IF NOT EXISTS idx_hypo_edges_child ON hypothesis_edges(child_id);
CREATE INDEX IF NOT EXISTS idx_hypo_status ON system_hypotheses(status);

-- Triggers to increment graph version on topology changes
CREATE TRIGGER IF NOT EXISTS trg_hypo_edge_insert
AFTER INSERT ON hypothesis_edges
BEGIN
    UPDATE cortex_meta 
    SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) 
    WHERE key = 'hypothesis_graph_version';
END;

CREATE TRIGGER IF NOT EXISTS trg_hypo_edge_delete
AFTER DELETE ON hypothesis_edges
BEGIN
    UPDATE cortex_meta 
    SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) 
    WHERE key = 'hypothesis_graph_version';
END;

CREATE TRIGGER IF NOT EXISTS trg_hypo_edge_update
AFTER UPDATE ON hypothesis_edges
BEGIN
    UPDATE cortex_meta 
    SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) 
    WHERE key = 'hypothesis_graph_version';
END;

-- When a new hypothesis is added, the graph version increments to re-index nodes
CREATE TRIGGER IF NOT EXISTS trg_hypo_node_insert
AFTER INSERT ON system_hypotheses
BEGIN
    UPDATE cortex_meta 
    SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) 
    WHERE key = 'hypothesis_graph_version';
END;
