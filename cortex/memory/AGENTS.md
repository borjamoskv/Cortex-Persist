<!-- [C5-REAL] Exergy-Maximized -->
# 🧠 AGENTS.md — `cortex/memory/`

> Scoped rules for the Memory domain. **Root `AGENTS.md` always takes precedence.**
> These rules augment — never contradict — the root contract.

---

## ⚠️ CRITICAL: Memory Surface Safety Gate

The `memory/` directory has the **largest public API surface** in CORTEX and is the most sensitive to state corruption, tenant leakage, and fact aging violations.

**Before touching ANY file in this directory:**
1. Verify tenant isolation is preserved — every read/write path MUST be tenant-scoped.
2. Check `guardrails.py` is in the call stack for any fact insertion.
3. Confirm `ledger.py` (local to memory/) emits an event for any state mutation.
4. Run `pytest tests/ -k "memory" -v` before and after your change.

---

## Memory Module Risk Map

| Module | Risk | Rule |
| :--- | :---: | :--- |
| `ledger.py` | **CRITICAL** | Hash-chain continuity. Every write must chain to the previous hash. Never break the chain. |
| `guardrails.py` | **CRITICAL** | Admission gate for memory writes. Do not add permissive bypass conditions. |
| `episodic.py` | **HIGH** | Episodic memory aging. Time-based operations MUST use deterministic timestamps, not `datetime.now()`. |
| `engrams.py` | **HIGH** | Long-term memory encoding. Mutations here affect retrieval fidelity across all tenants. |
| `crdt.py` | **HIGH** | Conflict-free replicated data type. Any change MUST preserve commutativity and idempotency. |
| `consolidation.py` | **HIGH** | Memory consolidation runs merge operations. Always test with multi-tenant fixtures. |
| `drift.py` | MEDIUM | Memory drift detection. Read-only analysis path — do not make writes here. |
| `compression.py` | MEDIUM | Lossy compression of low-salience facts. Compression is irreversible — verify salience gates. |
| `dream.py` | MEDIUM | Offline consolidation daemon. Cannot run concurrently with `consolidation.py`. |

---

## Tenant Isolation Invariants

Every function in this directory that touches persistent state MUST:

1. Accept and pass `tenant_id` as an explicit parameter — no implicit global state.
2. Filter all SQL queries by `tenant_id` before execution.
3. Never expose cross-tenant facts in any return value.

```python
# ✅ CORRECT
async def get_facts(self, tenant_id: str, query: str) -> list[Fact]:
    ...WHERE tenant_id = ?...

# ❌ VIOLATION — no tenant scope
async def get_facts(self, query: str) -> list[Fact]:
    ...WHERE content LIKE ?...
```

---

## Fact Aging Protocol

Facts in memory are subject to temporal decay via `drift.py` and `frequency.py`. When modifying aging logic:

- Never remove salience floors — a fact's minimum retention MUST be > 0.
- Age-based eviction MUST emit a Ledger event before deletion.
- `episodic.py` retention windows are tenant-configurable — do not hardcode defaults.

---

## Memory Test Coverage Requirement

```bash
pytest tests/ -k "memory or tenant or ledger or fact" -v --cov=cortex/memory
```

Minimum coverage gate: **85%** on modified modules. Higher bar than engine due to public API surface.
