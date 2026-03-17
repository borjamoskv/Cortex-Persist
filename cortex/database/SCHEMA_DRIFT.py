"""CORTEX Schema Drift Documentation.

The live database (~/.cortex/cortex.db) has EVOLVED beyond the DDL
defined in cortex/database/schema.py. This is a known and documented state.

Live DB: 32 columns in `facts` table (accumulated via ALTER TABLE over time).
DDL:     16 columns (the "target" clean schema).
Migration (mig_simplify_facts.py): 11 columns (aggressive simplification, NOT APPLIED).

Key invariant: All SELECT queries use named columns (not SELECT *),
so the 32-column live schema does NOT break queries that SELECT 16 named columns.

The extra 16 columns are:
  - timestamp (REAL) — legacy, replaced by created_at/updated_at
  - cognitive_layer — moved to metadata JSON
  - parent_decision_id — moved to metadata JSON
  - is_diamond, is_bridge — unused classification flags
  - success_rate — unused scoring metric
  - source_metadata, access_stats — JSON blobs, orphaned
  - tx_id — moved to metadata JSON
  - exergy, pinned — metabolism fields, referenced by metabolism subsystem
  - verification_status, provenance_json, claims_json, signatures_json,
    last_revalidated_at — verification subsystem fields

DO NOT:
  - Run CREATE TABLE IF NOT EXISTS on a DB that already has `facts` (it's a no-op anyway)
  - Run mig_simplify_facts without backup and explicit operator approval
  - Use SELECT * anywhere in production code
  - Assume column positions match DDL order (use named columns always)
"""
