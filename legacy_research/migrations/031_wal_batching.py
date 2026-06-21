UP = """
CREATE TABLE batch_wal (
    event_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    received_at_epoch_ms BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'sealed', 'rejected'))
);

CREATE INDEX idx_batch_wal_status ON batch_wal(status);

CREATE TABLE sealed_batches (
    batch_id TEXT PRIMARY KEY,
    merkle_root TEXT NOT NULL,
    event_count INT NOT NULL,
    sealed_at TIMESTAMP NOT NULL,
    wal_snapshot BIGINT NOT NULL
);
"""
