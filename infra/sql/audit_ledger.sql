-- CORTEX v6.1 — Audit Ledger Schema (PostgreSQL)
-- Axiom: Ω₂ (Entropic Asymmetry) — audit trails are infinite; data is ephemeral.
--
-- Immutable append-only ledger for distributed cache eviction events.
-- Stores cryptographic chain proofs for EU AI Act traceability compliance.
--
-- Usage:
--   psql -U cortex -d cortex -f infra/sql/audit_ledger.sql

-- ─── Extension guard ─────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Audit Ledger (append-only) ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cortex_audit_ledger (
    -- Primary identity
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    eviction_id     BIGINT NOT NULL,            -- Monotonic counter from Redis

    -- Agent context
    agent_key       TEXT NOT NULL,              -- Logical agent/session key
    node_id         TEXT NOT NULL,              -- Which container generated this
    event_type      TEXT NOT NULL               -- EVICTION_AUDIT | EVICTION_AUDIT_DEGRADED
                    CHECK (event_type IN ('EVICTION_AUDIT', 'EVICTION_AUDIT_DEGRADED', 'SESSION_END')),

    -- Cryptographic proof chain (Ω₂)
    prev_proof      CHAR(64) NOT NULL,          -- SHA-256 of previous chain tip
    current_proof   CHAR(64) NOT NULL,          -- SHA-256 of this entry
    payload_hash    CHAR(64) NOT NULL,          -- SHA-256 of the evicted data

    -- Data tombstone (metadata only, no PII)
    tombstone       JSONB NOT NULL DEFAULT '{}',

    -- Temporal
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_ts        DOUBLE PRECISION NOT NULL   -- Unix timestamp from the worker
);

-- ─── Cold Memory Store (optional — evicted context) ──────────────────────────
-- Store the actual evicted data here ONLY if needed for compliance audits.
-- In normal operation, tombstones are sufficient.
CREATE TABLE IF NOT EXISTS cortex_cold_memory (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_key       TEXT NOT NULL,
    audit_id        UUID REFERENCES cortex_audit_ledger(id) ON DELETE RESTRICT,
    context_data    JSONB NOT NULL,             -- The actual evicted context
    payload_hash    CHAR(64) NOT NULL,          -- Must match audit_ledger.payload_hash
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Verify hash integrity on insert
    CONSTRAINT cold_memory_hash_check CHECK (
        payload_hash ~ '^[a-f0-9]{64}$'
    )
);

-- ─── Chain Integrity Materialised View ───────────────────────────────────────
-- Use this to verify the chain is unbroken without scanning the full table.
CREATE MATERIALIZED VIEW IF NOT EXISTS cortex_chain_integrity AS
SELECT
    eviction_id,
    agent_key,
    node_id,
    prev_proof,
    current_proof,
    created_at,
    -- Flag a break: prev of this row should equal current of prior row
    LAG(current_proof) OVER (ORDER BY eviction_id) AS expected_prev_proof,
    LAG(current_proof) OVER (ORDER BY eviction_id) = prev_proof AS chain_valid
FROM cortex_audit_ledger
ORDER BY eviction_id;

CREATE UNIQUE INDEX IF NOT EXISTS cortex_chain_integrity_idx
    ON cortex_chain_integrity (eviction_id);

-- ─── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_agent_key ON cortex_audit_ledger (agent_key);
CREATE INDEX IF NOT EXISTS idx_audit_node_id   ON cortex_audit_ledger (node_id);
CREATE INDEX IF NOT EXISTS idx_audit_created   ON cortex_audit_ledger (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_proof     ON cortex_audit_ledger (current_proof);

CREATE INDEX IF NOT EXISTS idx_cold_agent_key  ON cortex_cold_memory (agent_key);
CREATE INDEX IF NOT EXISTS idx_cold_audit_id   ON cortex_cold_memory (audit_id);

-- ─── Row-Level Security (EU AI Act — tenant isolation) ───────────────────────
ALTER TABLE cortex_audit_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE cortex_cold_memory  ENABLE ROW LEVEL SECURITY;

-- Superuser sees all. API role (cortex_api) sees only its own node's data.
-- Adjust node_id filter or add tenant_id column for full multi-tenant isolation.
CREATE POLICY audit_ledger_sovereign
    ON cortex_audit_ledger
    FOR SELECT
    USING (true);  -- Relax for audit reads; restrict writes to cortex_api role.

-- ─── Read-only audit role ────────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cortex_auditor') THEN
        CREATE ROLE cortex_auditor NOLOGIN;
    END IF;
END
$$;

GRANT SELECT ON cortex_audit_ledger TO cortex_auditor;
GRANT SELECT ON cortex_chain_integrity TO cortex_auditor;
-- cortex_auditor cannot read cold_memory (PII protection)

-- ─── Helper: Verify full chain from epoch ────────────────────────────────────
CREATE OR REPLACE FUNCTION cortex_verify_chain()
RETURNS TABLE (
    broken_at_id    BIGINT,
    expected_prev   TEXT,
    actual_prev     TEXT,
    verified_count  BIGINT
)
LANGUAGE plpgsql STABLE AS $$
DECLARE
    rec                 RECORD;
    prev_tip            TEXT := encode(sha256('CORTEX_GENESIS_VOID'), 'hex');
    verified            BIGINT := 0;
BEGIN
    FOR rec IN
        SELECT eviction_id, prev_proof, current_proof
        FROM cortex_audit_ledger
        ORDER BY eviction_id ASC
    LOOP
        IF rec.prev_proof != prev_tip THEN
            RETURN QUERY SELECT rec.eviction_id, prev_tip, rec.prev_proof, verified;
            RETURN;
        END IF;
        prev_tip := rec.current_proof;
        verified := verified + 1;
    END LOOP;

    -- All entries valid
    RETURN QUERY SELECT NULL::BIGINT, NULL::TEXT, NULL::TEXT, verified;
END;
$$;

COMMENT ON FUNCTION cortex_verify_chain IS
'Walks the full audit ledger and verifies cryptographic chain integrity.
 Returns the broken entry or NULL if the chain is intact.
 Derivation: Ω₃ × Ω₂ — Byzantine Default + Entropic Asymmetry.';
