-- CORTEX Migration v16 — Crypto-Shredding (GDPR Right to Erasure).
--
-- Enables selective destruction of per-fact encryption keys.
-- The immutable ledger remains intact for EU AI Act auditing,
-- but the encrypted content becomes mathematically irrecoverable.
--
-- Axiom: Ω₃ (Byzantine Default) — Verify the shred, not the data.

CREATE TABLE IF NOT EXISTS shredded_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id     INTEGER NOT NULL,
    tenant_id   TEXT    NOT NULL DEFAULT 'default',
    reason      TEXT    NOT NULL DEFAULT 'gdpr_erasure',
    shredded_by TEXT,
    shredded_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(fact_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_shredded_fact_id
    ON shredded_keys(fact_id);

CREATE INDEX IF NOT EXISTS idx_shredded_tenant
    ON shredded_keys(tenant_id);
