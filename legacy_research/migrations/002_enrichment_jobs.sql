-- Migration: 002_enrichment_jobs.sql
-- Description: Adds the enrichment_jobs table for asynchronous processing of facts.
-- Part of P0 Decoupling (V6).

CREATE TABLE IF NOT EXISTS enrichment_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    job_type        TEXT NOT NULL DEFAULT 'embedding', -- 'embedding', 'summary', 'linkage'
    status          TEXT NOT NULL DEFAULT 'pending',   -- 'pending', 'processing', 'completed', 'failed'
    priority        INTEGER DEFAULT 0,
    attempts        INTEGER DEFAULT 0,
    last_error      TEXT,
    payload         TEXT,                              -- Optional JSON for specific job params
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_enrichment_jobs_status ON enrichment_jobs(status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_enrichment_jobs_fact ON enrichment_jobs(fact_id);
