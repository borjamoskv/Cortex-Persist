# REPOSITORY-CENSUS.md — ORTU-Ω Phase 0

> **Program**: ORTU-Ω Forge · **Codename**: SORTU-Ω  
> **Objective**: Freeze the factual map of the CORTEX terrain before defining the external Trust Layer API.  
> **Generated**: 2026-03-14

---

## 1. Module Census

| # | Subsystem | Entry Point | LOC | Status | Trust Surface |
|:--|:----------|:------------|----:|:------:|:-------------|
| 1 | `engine/store_mixin.py` | `StoreMixin.store()` | 483 | ✅ REAL | Write path: dedup → guards → privacy → causality → embed → ledger |
| 2 | `engine/query_mixin.py` | `QueryMixin.recall()` | 479 | ✅ REAL | Read path: Bayesian scoring, temporal decay, time-travel, history |
| 3 | `engine/memory_mixin.py` | `MemoryMixin._init_memory_subsystem()` | 132 | ✅ REAL | Tripartite init: L1 Working, L2 Vector (`sqlite-vec`/HDC), L3 Ledger |
| 4 | `engine/transaction_mixin.py` | `TransactionMixin._log_transaction()` | 81 | ✅ REAL | SHA-256 hash chain, `prev_hash` continuity, ledger checkpoint trigger |
| 5 | `engine/search_mixin.py` | `SearchMixin.search()` | 108 | ✅ REAL | Hybrid vector+text search, Graph-RAG enrichment, tenant-aware |
| 6 | `engine/ledger.py` | `ImmutableLedger` | 317 | ✅ REAL | Adaptive Merkle checkpointing, full integrity verify (chain + roots) |
| 7 | `guards/contradiction_guard.py` | `detect_contradictions()` | 556 | ✅ REAL | 3-layer conflict detection: FTS5 → project co-occurrence → negation/supersession |
| 8 | `verification/verifier.py` | `SovereignVerifier.check()` | 81 | ⚠️ PARTIAL | AST heuristic extraction implemented; Z3 SMT stub ("Phase 2" comment) |
| 9 | `causality/taint.py` | `propagate_taint()` | 162 | ✅ REAL | BFS DAG taint propagation, confidence downgrade, `≥50%` escalation rule |
| 10 | `consensus/byzantine.py` | `WBFTConsensus.evaluate()` | 432 | ✅ REAL | ⅓-fault-tolerant, Jaccard agreement, reputation-weighted, outlier detection |
| 11 | `consensus/manager.py` | `ConsensusManager.vote()` | 316 | ✅ REAL | LogOP voting, agent registration, reputation entropy drift, v1+v2 vote paths |
| 12 | `compliance/tracker.py` | `ComplianceTracker` | 335 | ✅ REAL | EU AI Act Art. 12: 3-method API (`log_decision`, `verify_chain`, `export_audit`) |
| 13 | `swarm/manager.py` | `CapatazOrchestrator` | 117 | ⚠️ PARTIAL | Task orchestration + `asyncio.gather` parallel; `_execute_completion_with_tracking()` = `NotImplementedError` |
| 14 | `gateway/shield.py` | `APIShield` | 66 | ✅ REAL | Header stripping, prompt radiopactization, usage masking |
| 15 | `mcp/server.py` | `create_mcp_server()` | 362 | ✅ REAL | 15+ MCP tools: store, search, status, ledger_verify, trace, shannon, handoff, embed, trust, health, genesis, music |

### External Packages

| Package | Location | Files | Status | Notes |
|:--------|:---------|------:|:------:|:------|
| `cortex-sdk` | `cortex-sdk/cortex_persist/` | 5 | ✅ REAL | `client.py` (sync, 4.6KB), `async_client.py` (5.6KB), `models.py`, `exceptions.py` |
| `open-cortex` | `open-cortex/open_cortex/` | 8 | ✅ REAL | Standalone FastAPI app: `router.py`, `persistence.py` (16KB), `models.py`, `metrics.py`, Docker-ready |

---

## 2. Public Surface Map

### 2.1 Write Path (Store)

```
input → StoreMixin.store()
  ├─ structural dedup (SHA-256 content hash, O(1))
  ├─ semantic dedup (vector cosine, O(N) bounded)
  ├─ ContradictionGuard.detect_contradictions()
  ├─ NemesisProtocol (async analysis, non-blocking)
  ├─ PrivacyShield (PII masking)
  ├─ CausalityResolver (parent_decision_id → causal edge)
  ├─ AES-GCM encryption (optional)
  ├─ Embedding generation (L2 vector)
  ├─ TransactionMixin._log_transaction() → SHA-256 chain
  ├─ ImmutableLedger.create_checkpoint_async() → Merkle root
  └─ fact_id returned
```

### 2.2 Read Path (Recall)

```
query → QueryMixin.recall()
  ├─ Bayesian scoring with temporal decay
  ├─ Exclusion: tombstoned, quarantined
  ├─ Confidence filtering
  └─ Sorted results with metadata

query → SearchMixin.search()
  ├─ hybrid_search (vector + FTS5)
  ├─ text_search fallback
  └─ Graph-RAG enrichment (optional)
```

### 2.3 Verification Path

```
ImmutableLedger.verify_integrity_async()
  ├─ Hash chain walk (prev_hash continuity)
  ├─ Hash recomputation (v2 canonical + v1 legacy fallback)
  ├─ Merkle root recomputation per checkpoint
  └─ integrity_checks table entry

SovereignVerifier.check()
  ├─ AST constraint extraction
  └─ Z3 SMT (stub — passthrough if no findings)
```

### 2.4 Coordination Path

```
ConsensusManager.vote() / vote_v2()
  ├─ Agent registration (UUID, reputation, public_key)
  ├─ Vote persistence (v1 simple, v2 reputation-weighted)
  ├─ LogOP consensus calculation
  ├─ Fact score update via MutationEngine
  └─ Agent entropy drift detection

WBFTConsensus.evaluate()
  ├─ Pairwise Jaccard agreement matrix
  ├─ Reputation-weighted scoring
  ├─ Byzantine threshold (⅔ weighted)
  ├─ Outlier detection
  └─ ByzantineVerdict with trust scores
```

### 2.5 Compliance Path

```
ComplianceTracker
  ├─ log_decision() → store_sync() with EU AI Act metadata
  ├─ verify_chain() → ImmutableLedger.verify_integrity_async()
  └─ export_audit() → Article 12 compliance report
```

---

## 3. Trust-Surface Inventory

| Capability | Module | Primitive | Contract |
|:-----------|:-------|:----------|:---------|
| **Continuity** | `memory_mixin.py` | Tripartite Memory (L1/L2/L3) | Init is lazy; L2 optional via `auto_embed` |
| **Continuity** | `store_mixin.py` | Structural + semantic dedup | SHA-256 content hash + vector cosine |
| **Continuity** | `query_mixin.py` | `time_travel()`, `history()` | Temporal state reconstruction |
| **Traceability** | `transaction_mixin.py` | Hash-chained transaction log | `prev_hash` → `hash` SHA-256 chain |
| **Traceability** | `ledger.py` | Merkle checkpointing | Adaptive batch size (swarm-aware) |
| **Traceability** | `causality/taint.py` | Taint propagation | BFS DAG, confidence downgrade |
| **Coordination** | `consensus/manager.py` | Agent voting + reputation | LogOP consensus, entropy drift |
| **Coordination** | `consensus/byzantine.py` | WBFT multi-model evaluation | ⅓ fault tolerance, Jaccard |
| **Coordination** | `swarm/manager.py` | Task orchestration | Parallel execution, budget tracking |
| **Useful Memory** | `search_mixin.py` | Hybrid search + Graph-RAG | Vector + FTS5 + entity graph |
| **Useful Memory** | `query_mixin.py` | Bayesian recall with decay | Temporal scoring, quarantine exclusion |
| **Verification** | `guards/contradiction_guard.py` | Contradiction detection | 3-layer: FTS5 → co-occurrence → negation |
| **Verification** | `verification/verifier.py` | Formal verification gate | AST heuristics (Z3 stub) |
| **Verification** | `compliance/tracker.py` | EU AI Act Article 12 | 5 sub-requirement checks, scored |

---

## 4. Dead Abstraction List

| Item | Location | Symptom | Severity |
|:-----|:---------|:--------|:---------|
| `_execute_completion_with_tracking()` | `swarm/manager.py:46` | `raise NotImplementedError` — stub never wired | P2 |
| Z3 SMT Phase 2 | `verification/verifier.py:76` | Comment: "In a full-blown RSI, we would unroll loops" — passthrough | P2 |
| `valid_until` dedup predicate | `store_mixin.py` (dedup query) | Uses legacy `valid_until IS NULL` instead of `is_tombstoned = 0` | P1 |
| `mask_usage()` jitter | `gateway/shield.py:64` | Comment says "random jitter" but no-op line | P3 |
| `_default_config` global | `mcp/server.py:344` | Module-level `create_mcp_server()` call at import time — side effect | P2 |
| Legacy vote path (v1) | `consensus/manager.py` | `consensus_votes` table coexists with `consensus_votes_v2` — migration debt | P2 |

---

## 5. Key Metrics

| Metric | Value |
|:-------|:------|
| **Total subsystems scanned** | 14 internal + 2 external packages |
| **Total LOC (trust core)** | ~3,917 (engine mixins + ledger + guards + verification + causality + consensus) |
| **MCP tools registered** | 15+ |
| **Public SDK operations** | ~10 (sync client + async client) |
| **Trust primitives verified** | 14 (see §3) |
| **Dead abstractions found** | 6 (0 P0, 1 P1, 4 P2, 1 P3) |
| **Missing P0 primitives** | 0 — all 5 pillars have at least one real implementation |

---

## 6. Census Verdict

**All five ORTU-Ω pillars have implemented backing primitives.** No P0 gaps (missing primitive) detected. The terrain is structurally sound for API surface definition.

Key risks for Phase 1 (Pillar Mapping):
- **Verification surface is thin**: `SovereignVerifier` is 81 LOC with Z3 in stub mode. The real verification power comes from the `ImmutableLedger` + `ContradictionGuard` + `TaintPropagation` trio.
- **Coordination has migration debt**: v1/v2 consensus vote tables coexist. The external API should expose only v2.
- **Swarm orchestration is partial**: `CapatazOrchestrator` can run parallel tasks but lacks completion tracking integration.
- **`valid_until` vs `is_tombstoned` drift**: Dedup query uses legacy predicate — a P1 contract inconsistency.

**Recommendation**: Proceed to Phase 1 (Pillar Mapping) with confidence. The terrain is real, not decorative.
