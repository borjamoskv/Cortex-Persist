# 🔧 AGENTS.md — `cortex/engine/`

> Scoped rules for the Engine domain. **Root `AGENTS.md` always takes precedence.**
> These rules augment — never contradict — the root contract.

---

## ⚠️ CRITICAL: Engine Mutation Safety Gate

The `engine/` directory is the **highest-risk surface** in CORTEX. Every mutation here has potential ledger and state integrity consequences.

**Before touching ANY file in this directory:**
1. Read the root Write-Path Contract (Saga Pattern) — no exceptions.
2. Identify which SAGA step your change affects.
3. Check whether `store_validation.py` or `store_mutation.py` are in the call stack.
4. Run `pytest tests/ -k "engine" -v` before and after your change.

---

## Kinetic Engine Safety — Annihilator & Crystallizer

The two most dangerous modules are:

| Module | Risk | Rule |
| :--- | :---: | :--- |
| `crystallizer.py` | CRITICAL | Never write without a prior guard call. Writes facts permanently to the ledger. |
| `reaper.py` | CRITICAL | Deletion is irreversible. Any call path through `reaper.py` MUST emit a Ledger event first. |
| `store_mutation.py` | CRITICAL | All mutations MUST pass through `store_validation.py` before execution. |
| `store_validation.py` | HIGH | Treat as the deterministic boundary. Do not add permissive fallbacks. |
| `slashing.py` | HIGH | Reputation slashing is irreversible per session. Requires double-validation. |
| `trust_registry.py` | HIGH | Identity mutations here propagate to all tenant-scoped operations. |
| `bridge_guard.py` | HIGH | Admission guard. Any softening of checks violates the Write-Path Contract (SAGA-1). |

---

## Engine-Specific Anti-Patterns

- **NO** direct SQLite writes bypassing `store_mutation.py`.
- **NO** calls to `crystallizer.py` without a prior `bridge_guard.py` admission check.
- **NO** modifications to `semantic_hash.py` without updating hash continuity tests.
- **NO** changes to `consensus.py` without verifying multi-agent quorum logic is intact.
- **NO** `evolution_engine.py` mutations that skip `evolution_metrics.py` instrumentation.
- **NO** `snapshots.py` writes without capturing `ROLLBACK_STATE` first (SAGA-6 invariant).

---

## Engine Test Coverage Requirement

Any engine change MUST maintain or improve coverage for:

```bash
pytest tests/ -k "engine or store or crystallizer or reaper" -v --cov=cortex/engine
```

Minimum coverage gate: **80%** on modified modules.
