-- CORTEX Migration v17 — HLC + CRDT Infrastructure.
--
-- Adds causal ordering and node identity to facts
-- for conflict-free replication across edge swarms.
--
-- Axiom: Ω₁₂ (Sovereign Autonomy) — Agents operate without a coordinator.

-- HLC timestamp for causal ordering (format: "physical_ms:logical_hex:node_id")
ALTER TABLE facts ADD COLUMN hlc_timestamp TEXT;

-- Node identity: which agent/device created this fact
ALTER TABLE facts ADD COLUMN node_id INTEGER DEFAULT 0;

-- Merge log: audit trail of swarm synchronization events
CREATE TABLE IF NOT EXISTS merge_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    local_node_id   INTEGER NOT NULL,
    remote_node_id  INTEGER NOT NULL,
    facts_added     INTEGER DEFAULT 0,
    facts_updated   INTEGER DEFAULT 0,
    facts_identical INTEGER DEFAULT 0,
    conflicts       INTEGER DEFAULT 0,
    tombstones      INTEGER DEFAULT 0,
    merged_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_facts_hlc ON facts(hlc_timestamp);
CREATE INDEX IF NOT EXISTS idx_facts_node ON facts(node_id);
CREATE INDEX IF NOT EXISTS idx_merge_log_nodes
    ON merge_log(local_node_id, remote_node_id);
