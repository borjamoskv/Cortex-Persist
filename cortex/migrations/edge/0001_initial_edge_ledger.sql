-- Migration number: 0001 	 2026-06-15T00:00:00.000Z
-- Initial schema for Cortex Persist Edge Ledger

CREATE TABLE IF NOT EXISTS edge_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taint TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_edge_ledger_taint ON edge_ledger(taint);
CREATE INDEX IF NOT EXISTS idx_edge_ledger_hash ON edge_ledger(payload_hash);
