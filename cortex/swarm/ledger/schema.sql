CREATE TABLE IF NOT EXISTS swarm_events (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id                TEXT NOT NULL UNIQUE,
    timestamp               TEXT NOT NULL,
    input_hash              TEXT NOT NULL,
    registry_hash           TEXT NOT NULL,
    task                    TEXT NOT NULL,
    selected_agent          TEXT NOT NULL,
    routing_payload         TEXT NOT NULL,
    deterministic_signature TEXT NOT NULL,
    version                 TEXT NOT NULL DEFAULT 'v2'
);

CREATE INDEX IF NOT EXISTS idx_swarm_task ON swarm_events (task);
CREATE INDEX IF NOT EXISTS idx_swarm_timestamp ON swarm_events (timestamp);
