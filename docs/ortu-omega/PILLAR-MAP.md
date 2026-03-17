# PILLAR-MAP.md — ORTU-Ω Phase 1

> **Program**: ORTU-Ω Forge · **Codename**: SORTU-Ω  
> **Input**: [REPOSITORY-CENSUS.md](file://./docs/ortu-omega/REPOSITORY-CENSUS.md)  
> **Generated**: 2026-03-14

---

## 1. Pillar Matrix

### 🟢 Pillar 1 — Continuity

> Agent state persists across sessions, contexts, and crashes.

| Primitive | Module | LOC | Status | Evidence |
|:----------|:-------|----:|:------:|:---------|
| Tripartite Memory init | `engine/memory_mixin.py` | 132 | ✅ | L1 Working + L2 Vector (`sqlite-vec`/HDC) + L3 Ledger. Lazy init, `auto_embed` toggle |
| Structural dedup | `engine/store_mixin.py` | 483 | ✅ | SHA-256 content hash, O(1) lookup before insert |
| Semantic dedup | `engine/store_mixin.py` | — | ✅ | Vector cosine similarity, O(N) bounded, configurable threshold |
| Temporal state reconstruction | `engine/query_mixin.py` | 479 | ✅ | `time_travel(as_of)`, `history(fact_id)`, `reconstruct_state(project, as_of)` |
| AES-GCM encryption at rest | `engine/store_mixin.py` | — | ✅ | Optional per-tenant encryption, keyring-backed |
| Sync + async duality | `CortexEngine` | — | ✅ | `store()` + `store_sync()`, `recall()` + `recall_sync()` |

**Gaps:**

| Gap | Severity | Detail |
|:----|:--------:|:-------|
| Session state not portable | **P2** | No export/import format for agent working memory (L1). Agent dies → L1 lost |
| Crash recovery untested | **P2** | No documented recovery protocol if write fails mid-transaction. SQLite WAL provides implicit safety, but no explicit checkpoint-on-resume |
| `valid_until` vs `is_tombstoned` drift | **P1** | Dedup query uses `valid_until IS NULL` instead of `is_tombstoned = 0`. Contract inconsistency |

**Risks:**
- L2 init fails silently if `sentence-transformers` unavailable → agents fall back to text-only recall without warning
- HDC path (`CORTEX_HDC=1`) is environment-variable gated — no runtime toggle

**SDK-Exposable:** `store`, `recall`, `time_travel`, `history` — all via typed wrappers  
**Open-Core:** ✅ Full — continuity is the core value proposition

---

### 🟢 Pillar 2 — Traceability

> Every decision is hash-chained, auditable, and reproducible.

| Primitive | Module | LOC | Status | Evidence |
|:----------|:-------|----:|:------:|:---------|
| SHA-256 hash chain | `engine/transaction_mixin.py` | 81 | ✅ | `prev_hash` → `hash` chain. GENESIS block. Every mutation logged |
| Merkle checkpointing | `engine/ledger.py` | 317 | ✅ | Adaptive batch size (swarm-aware), `merkle_roots` table, full recomputation verify |
| Full integrity verification | `engine/ledger.py` | — | ✅ | `verify_integrity_async()`: chain walk + hash recomputation (v2 + v1 legacy) + Merkle root verify |
| Taint propagation | `causality/taint.py` | 162 | ✅ | BFS DAG traversal, `≥50%` tainted parents → escalation, confidence downgrade |
| Causal edge tracking | `engine/store_mixin.py` | — | ✅ | `parent_decision_id` → `causal_edges` table. Automatic causality resolution |
| Compliance audit | `compliance/tracker.py` | 335 | ✅ | EU AI Act Art. 12: `log_decision()`, `verify_chain()`, `export_audit()` |

**Gaps:**

| Gap | Severity | Detail |
|:----|:--------:|:-------|
| No standard export format | **P2** | Audit trail exists but no JSON-LD / SARIF / SPDX export. Internal format only |
| Taint propagation is in-memory only | **P2** | `propagate_taint()` operates on `dict[str, FactNode]` graph — must be hydrated from DB first. No persistent taint status column |
| No trace visualization | **P3** | Causal DAG exists but no serialization to DOT/Mermaid for external rendering |

**Risks:**
- Hash computation has v1/v2 dual path (`compute_tx_hash` / `compute_tx_hash_v1`). Legacy chain coexists with canonical — migration never forced
- `integrity_checks` table records results but no alerting mechanism

**SDK-Exposable:** `verify`, `trace`, `audit_report`, `taint_status`  
**Open-Core:** ✅ Full — traceability is a differentiator for compliance buyers

---

### 🟡 Pillar 3 — Coordination

> Multi-agent consensus with Byzantine fault tolerance.

| Primitive | Module | LOC | Status | Evidence |
|:----------|:-------|----:|:------:|:---------|
| Agent registration | `consensus/manager.py` | 316 | ✅ | UUID agent, type, public_key, reputation_score, tenant isolation |
| LogOP consensus voting (v2) | `consensus/manager.py` | — | ✅ | Reputation-weighted logit aggregation, quadratic weight suppression |
| WBFT multi-model evaluation | `consensus/byzantine.py` | 432 | ✅ | ⅓ fault tolerance, Jaccard agreement, reputation decay, outlier detection |
| Agent entropy drift | `consensus/manager.py` | — | ✅ | `alignment_hits`/`alignment_misses` tracking, reputation penalty on drift |
| Task orchestration | `swarm/manager.py` | 117 | ⚠️ | `asyncio.gather` parallel. `_execute_completion_with_tracking` = `NotImplementedError` |
| Legacy vote path (v1) | `consensus/manager.py` | — | ⚠️ | `consensus_votes` table still active alongside v2 — migration debt |

**Gaps:**

| Gap | Severity | Detail |
|:----|:--------:|:-------|
| No external event bus | **P1** | Coordination events are Pulse signals (internal). No webhook/SSE/pubsub for external agents |
| Swarm completion tracking | **P2** | `_execute_completion_with_tracking()` raises `NotImplementedError` |
| v1/v2 vote table coexistence | **P2** | Two parallel vote tables. External API must expose only v2 but fallback complicates cleanup |
| No agent heartbeat protocol | **P2** | Agents are registered but no liveness check. Stale agents accumulate reputation silently |

**Risks:**
- WBFT `byzantine.py` depends on `cortex.thinking.fusion_models` (tight coupling to LLM-specific types)
- `ConsensusManager` directly accesses `engine.get_conn()` — no connection pooling boundary

**SDK-Exposable:** `register_agent`, `vote`, `consensus_status`, `swarm_event` (with event bus gap closed)  
**Open-Core:** ⚠️ Partial — agent registration + basic vote = open. WBFT + reputation = premium

---

### 🟢 Pillar 4 — Useful Memory

> Tripartite recall (working/vector/episodic) with compaction and forgetting.

| Primitive | Module | LOC | Status | Evidence |
|:----------|:-------|----:|:------:|:---------|
| Bayesian recall with temporal decay | `engine/query_mixin.py` | 479 | ✅ | Scoring with `recency_boost`, quarantine/tombstone exclusion, confidence filtering |
| Hybrid search (vector + text) | `engine/search_mixin.py` | 108 | ✅ | `hybrid_search()` + `text_search()` fallback. `sqlite-vec` embeddings |
| Graph-RAG enrichment | `engine/search_mixin.py` | — | ✅ | Entity extraction → subgraph traversal → `graph_context` attached to results |
| FTS5 full-text index | Database schema | — | ✅ | `facts_fts` table with automatic indexing |
| Working Memory (L1) | `memory/working.py` | — | ✅ | In-process context buffer, session-scoped |
| Compaction | `compaction/compactor.py` | — | ✅ | Duplicate elimination, semantic clustering, crystal synthesis |

**Gaps:**

| Gap | Severity | Detail |
|:----|:--------:|:-------|
| No unified recall API | **P1** | `recall()` (Bayesian) and `search()` (hybrid) are separate methods with different signatures and semantics. Consumer must choose |
| L1 not serializable | **P2** | Working Memory is in-process dict — not portable, not snapshotable |
| No forgetting policy API | **P2** | Forgetting oracle exists internally but not exposable as a policy configuration |

**Risks:**
- `search()` requires `auto_embed=True` for vector path — if embedder fails, silently falls to text
- `Graph-RAG` entity extraction uses regex heuristics — no NER model

**SDK-Exposable:** `recall`, `search`, `compact`, `memory_stats`  
**Open-Core:** ✅ Full — useful memory is the primary developer experience

---

### 🟡 Pillar 5 — Verification Surface

> Guards, invariants, taint propagation, and rejection semantics.

| Primitive | Module | LOC | Status | Evidence |
|:----------|:-------|----:|:------:|:---------|
| Contradiction Guard | `guards/contradiction_guard.py` | 556 | ✅ | 3-layer detection: FTS5 keyword → project co-occurrence → negation/supersession |
| Taint Propagation | `causality/taint.py` | 162 | ✅ | BFS DAG, confidence downgrade (C5→C1 in steps), `≥50%` parent escalation |
| Formal Verification Gate | `verification/verifier.py` | 81 | ⚠️ | AST heuristic extraction works. Z3 SMT = stub (passthrough) |
| Immune Membrane | `immune/membrane.py` | — | ✅ | `ImmuneMembrane.intercept()` → `Verdict.PASS/HOLD/BLOCK`. Used in MCP store/search |
| Privacy Shield | `guards/privacy_shield.py` | — | ✅ | PII masking at store-time |
| MCP Guard | `mcp/guard.py` | — | ✅ | Input validation for MCP tool calls |
| EU AI Act Compliance | `compliance/tracker.py` | 335 | ✅ | 5 Article 12 sub-requirement checks with evidence |

**Gaps:**

| Gap | Severity | Detail |
|:----|:--------:|:-------|
| No rejection API | **P1** | Guards reject internally but there's no typed `RejectionResult` returned to the caller with actionable remediation |
| Z3 SMT = passthrough | **P2** | `SovereignVerifier` reports `Z3_UNSAT_BY_AST_PROXIMAL` when no AST findings — not a real formal proof |
| No policy configuration | **P2** | Guards are hardcoded thresholds. No way for external consumers to tune contradiction sensitivity or taint escalation rules |
| Taint not persisted | **P2** | See Pillar 2 — `propagate_taint()` operates on ephemeral graph, results not written back to DB |

**Risks:**
- `SovereignVerifier` is 81 LOC — the thinnest trust surface. Real verification power lies in the ledger+guard+taint trio
- `ImmuneMembrane` filters are configurable but filter registry is not exposed

**SDK-Exposable:** `verify`, `taint_status`, `guard_check`, `compliance_report`  
**Open-Core:** ⚠️ Partial — basic guards + ledger verify = open. Taint propagation + immune membrane + compliance = premium

---

## 2. Gap Summary

| Severity | Count | Key Items |
|:---------|------:|:----------|
| **P0** (missing primitive) | 0 | — |
| **P1** (broken contract) | 4 | No unified recall API, no external event bus, no rejection API, dedup predicate drift |
| **P2** (packaging issue) | 11 | Session portability, crash recovery, export format, taint persistence, v1/v2 vote debt, swarm tracking, L1 serialization, forgetting policy, Z3 stub, policy config, agent heartbeat |
| **P3** (polish) | 1 | Trace visualization |

---

## 3. Open-Core Boundary

| Layer | Scope | License |
|:------|:------|:--------|
| **Open** | Store, recall, search, verify (ledger), basic guards, dedup, FTS5, SQLite persistence | Apache-2.0 |
| **Premium** | WBFT consensus, reputation management, taint propagation, immune membrane, EU AI Act compliance, Graph-RAG, compaction | BSL → Apache-2.0 (2030) |
| **Deferred** | Z3 formal proofs, multi-cloud (AlloyDB/Qdrant), advanced swarm orchestration | Not in v1 |

---

## 4. Phase 1 Verdict

**All 5 pillars are structurally backed.** No P0 gaps. The 4 P1 gaps are interface-level problems, not missing capabilities:

1. **Unified recall** → merge `recall()` + `search()` behind a single `query()` operation with strategy parameter
2. **External event bus** → expose coordination events via SSE/webhook adapter on the existing Pulse signal bus
3. **Rejection API** → wrap guard/membrane verdicts in a typed `RejectionResult` with remediation hints
4. **Dedup predicate drift** → fix `valid_until IS NULL` → `is_tombstoned = 0` in `store_mixin.py`

**Recommendation**: Proceed to Phase 2 (API Surface Definition). The primitives exist — what's missing is the **composable external contract** that wraps them.
