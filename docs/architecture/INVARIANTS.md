# DB Invariants — Operational Contract

This document is the **machine-verifiable constitution** of the CORTEX storage engine.
Every invariant listed here is enforced by `scripts/verify_db_invariants.py` and
gated in CI by `.github/workflows/ci.yml`.

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
| `INV-005` | Ledger hash-chain integrity: no transaction with a broken `prev_hash` link | Verified by the ledger verifier (`cortex verify`) |
| `INV-006` | No tombstoned facts still indexed in FTS | `SELECT count(*) FROM facts_fts WHERE rowid IN (SELECT id FROM facts WHERE is_tombstoned=1)` |
| `INV-007` | `facts_fts` row count matches non-tombstoned, non-quarantined `facts` count | `count(facts_fts)` == `count(facts WHERE is_tombstoned=0 AND is_quarantined=0)` |

## Soft Invariants (threshold-based)

These are probabilistic health signals with configurable thresholds.
Violations produce `WARN` in local runs and `FAIL` in CI.

| ID | Invariant | Default Threshold |
|----|-----------|-------------------|
| `INV-010` | Tombstone ratio < 5% of total active facts | `tombstoned / total < 0.05` |
| `INV-011` | Quarantine rate < 1% of total ingested | `quarantined / total < 0.01` |
| `INV-012` | Dedup lookup p95 latency < 10 ms | See `scripts/benchmark_hot_paths.py` |
| `INV-013` | FTS search p95 latency < 15 ms | See `scripts/benchmark_hot_paths.py` |
| `INV-014` | Vector lookup (ANN) p95 latency < 20 ms | See `scripts/benchmark_hot_paths.py` |
| `INV-015` | Causal graph orphan edges < 0.1% of total edges | `orphan_edges / total_edges < 0.001` |

## Drift Telemetry Counters

Persistent counters emitted to `artifacts/health/system_integrity_report.json` on every run:

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
| Local dev | `python scripts/verify_db_invariants.py` |
| Pre-push hook | `scripts/verify_db_invariants.py --strict` in `.pre-commit-config.yaml` |
| CI gate | `.github/workflows/ci.yml` → `invariant-check` job → blocks merge |
| Regression suite | `tests/integration/test_db_invariants.py` |

## Mutation Policy

Any PR that touches `cortex/database/`, `cortex/migrations/`, `cortex/engine/`, or `cortex/memory/`
**must** include:
1. A migration that passes `verify_db_invariants.py --strict`.
2. A regression test proving the new invariant holds post-mutation.
3. Updated thresholds in this document if benchmarks change.

No exceptions. Silent invariant violations = trust layer compromise.
