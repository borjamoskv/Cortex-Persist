<!-- [C5-REAL] Exergy-Maximized -->
# DB Invariants — Operational Contract

This document is the **architectural contract** for the CORTEX storage engine.
In the current tree snapshot there is no single `scripts/verify_db_invariants.py`
gate; enforcement is split across ledger verification, health checks, and targeted
tests gated by `.github/workflows/ci.yml`.

If any invariant is violated, the system is in a degraded state.
Fix → verify → commit. No exceptions.

---

## Hard Invariants (zero-tolerance)

These conditions must hold on every healthy database. A single violation = `FAIL`.

| ID | Invariant | SQL Probe |
|----|-----------|-----------|
| `INV-001` | No orphan FTS rows (rows in `facts_fts` with no matching row in `facts`) | `SELECT count(*) FROM facts_fts WHERE rowid NOT IN (SELECT id FROM facts)` |
| `INV-002` | No orphan causal edges (edges referencing a non-existent fact) | `SELECT count(*) FROM causal_edges WHERE fact_id NOT IN (SELECT id FROM facts)` |
| `INV-003` | No quarantined facts in the active index | `SELECT count(*) FROM facts WHERE is_quarantined=1 AND valid_until IS NULL AND is_tombstoned=0` |
| `INV-004` | Hash backfill coverage 100% for active, non-tombstoned facts | `SELECT count(*) FROM facts WHERE hash IS NULL AND is_tombstoned=0 AND is_quarantined=0` must be 0 |
| `INV-005` | Ledger hash-chain integrity: no transaction with a broken `prev_hash` link | Verified by the current trust-ledger surface (`cortex trust-ledger verify`) |
| `INV-006` | No tombstoned facts still indexed in FTS | `SELECT count(*) FROM facts_fts WHERE rowid IN (SELECT id FROM facts WHERE is_tombstoned=1)` |
| `INV-007` | `facts_fts` row count matches non-tombstoned, non-quarantined `facts` count | `count(facts_fts)` == `count(facts WHERE is_tombstoned=0 AND is_quarantined=0)` |

## Soft Invariants (threshold-based)

These are probabilistic health signals with configurable thresholds.
Violations produce `WARN` in local runs and `FAIL` in CI.

| ID | Invariant | Default Threshold |
|----|-----------|-------------------|
| `INV-010` | Tombstone ratio < 5% of total active facts | `tombstoned / total < 0.05` |
| `INV-011` | Quarantine rate < 1% of total ingested | `quarantined / total < 0.01` |
| `INV-012` | Dedup lookup p95 latency < 10 ms | Historical target threshold; no dedicated `scripts/benchmark_hot_paths.py` is present in this tree |
| `INV-013` | FTS search p95 latency < 15 ms | Historical target threshold; benchmark wiring should be documented separately before being treated as enforced |
| `INV-014` | Vector lookup (ANN) p95 latency < 20 ms | Historical target threshold; benchmark wiring should be documented separately before being treated as enforced |
| `INV-015` | Causal graph orphan edges < 0.1% of total edges | `orphan_edges / total_edges < 0.001` |

## Drift Telemetry Counters

Target-state counters for a structural integrity report. The file
`artifacts/health/system_integrity_report.json` is not present in this tree snapshot,
so treat the list below as doctrine rather than a guaranteed emitted artifact:

```
ingested_total          — lifetime facts stored
dedup_hits_total        — lifetime dedup collisions
quarantine_total        — facts routed to quarantine
orphan_fts_repairs      — FTS orphan rows auto-repaired
orphan_causal_repairs   — causal orphan edges repaired
namespace_rewrites      — project namespace normalizations
hash_backfill_writes    — retroactive hash backfills
integrity_failures      — invariant failures since last clean state
```

Derived velocity ratios (computed at check time, not stored):
```
dedup_hit_rate          = dedup_hits_total / ingested_total
quarantine_rate         = quarantine_total / ingested_total
repair_rate             = (orphan_fts_repairs + orphan_causal_repairs) / ingested_total
drift_velocity          = integrity_failures / ingested_total  (if > 0 → investigate)
```

## Enforcement Surface

| Where | How |
|-------|-----|
| Local dev | `python3 -m cortex.cli trust-ledger verify` plus targeted tests for storage and tenant isolation |
| Pre-push hook | `pre-commit run --all-files` (current local hook runs fast tests, not a dedicated DB invariant script) |
| CI gate | `.github/workflows/ci.yml` → `test`, `lint`, and `security` jobs |
| Regression suite | Representative current tests include `tests/test_storage_fail_closed.py`, `tests/test_tenant_isolation.py`, and `tests/health/test_health.py` |

## Mutation Policy

Any PR that touches `legacy_research/database/`, `cortex/migrations/`, `cortex/engine/`, or `cortex/memory/`
**must** include:
1. A migration that passes `verify_db_invariants.py --strict`.
2. Regression coverage proving the new invariant still holds post-mutation.
3. Updated thresholds in this document if benchmarks change.

No exceptions. Silent invariant violations = trust layer compromise.
