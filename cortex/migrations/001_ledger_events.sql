CREATE TABLE IF NOT EXISTS ledger_events (
    event_id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    tool TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    semantic_status TEXT NOT NULL DEFAULT 'pending',
    semantic_error TEXT,
    correlation_id TEXT,
    trace_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_ledger_events_ts ON ledger_events(ts);
CREATE INDEX IF NOT EXISTS idx_ledger_events_semantic_status ON ledger_events(semantic_status);
