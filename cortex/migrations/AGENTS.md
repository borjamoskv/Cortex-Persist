<!-- [C5-REAL] Exergy-Maximized -->
# 🗄️ AGENTS.md — `cortex/migrations/`

> Scoped rules for the Migrations domain. **Root `AGENTS.md` always takes precedence.**
> These rules augment — never contradict — the root contract.

---

## ⚠️ CRITICAL: Migrations are Irreversible in Production

Schema changes carry the highest blast radius of any operation in CORTEX. A broken migration can corrupt the ledger hash chain, invalidate tenant data, or cause silent data loss.

**STOP. Before writing or applying any migration:**

```text
1. Run:  alembic history --verbose
         → Read the full output. Understand the current head before proceeding.

2. Run:  alembic current
         → Confirm the database is at the expected revision.

3. Ask:  Can this migration be rolled back? What is the exact downgrade target?
         → Document the answer in the migration file header.

4. Ask:  Does this change affect vec0 (sqlite-vec) virtual tables?
         → If YES: test in an environment with sqlite-vec loaded. Many CI environments lack this.

5. Run:  alembic upgrade head --sql  (dry-run, prints SQL only — does not apply)
         → Review SQL before applying.
```

---

## Migration File Inventory

| File | Applies To | Notes |
| :--- | :--- | :--- |
| `001_ledger_events.sql` | Ledger hash chain | Foundation. Never modify without full chain re-verification. |
| `002_enrichment_jobs.sql` | Enrichment queue | Modifying column types here breaks `enrichment_worker.py`. |
| `016_crypto_shredding.sql` | Encryption keys | Crypto shredding is permanent. Test tenant key rotation first. |
| `017_hlc_crdt.sql` | HLC timestamps + CRDT | HLC ordering is global. Changes affect all inter-agent sync operations. |
| `mig_cognitive_layer.py` | Cognitive maps | Embedded vector schema. Requires `sqlite-vec` loaded. |
| `mig_consensus.py` | Consensus tables | Quorum logic depends on this schema. Breaks multi-agent sync if wrong. |

---

## Migration Acceptance Rules

A migration is **REJECTED** if any of the following are true:

- [ ] No `# DOWNGRADE TARGET: revision_id` comment in the migration header.
- [ ] Drops a column without a data-preservation strategy documented.
- [ ] Alters a column type without a cast/coercion path verified.
- [ ] Touches `ledger_events` without a full hash-chain re-verification test.
- [ ] Modifies `vec0` virtual tables without an environment test where `sqlite-vec` is absent (graceful degradation check).
- [ ] Has no corresponding `pytest` fixture that verifies the schema state post-migration.

---

## Emergency Rollback Procedure

If a migration causes a production failure:

```bash
# 1. Identify current broken head
alembic current

# 2. Roll back to last known good state
alembic downgrade <previous_revision_id>

# 3. Lock write paths immediately (prevent further data mutation)
# Set CORTEX_READONLY_MODE=1 in environment

# 4. Emit incident to Ledger with blast radius assessment
# 5. Do NOT attempt forward migration without root cause identified
```
