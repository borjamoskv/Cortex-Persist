# IMPLEMENTATION-PLAN.md — ORTU-Ω Phase 3

> **Program**: ORTU-Ω Forge · **Codename**: SORTU-Ω  
> **Input**: [PILLAR-MAP.md](file://./docs/ortu-omega/PILLAR-MAP.md) · [API-SURFACE.md](file://./docs/ortu-omega/API-SURFACE.md)  
> **Generated**: 2026-03-14

---

## 1. Executive Summary

This plan translates the Phase 1 Gap Analysis and Phase 2 API Surface into an executable roadmap.
The core realization: **CORTEX does not lack capabilities (0 P0 gaps); it lacks a coherent public topology (4 P1 interface gaps).**

The goal is not to invent new internal engines, but to package the existing trust infrastructure into a reliable, typed, and observable product. We focus strictly on the `cortex-sdk` layer and the boundaries separating internal implementations from public consumption.

---

## 2. P1 Gap Resolution Index

| Gap | Root Cause | Target State | Resolution Workstream |
|:---|:---|:---|:---|
| **Unified Recall API** | Internal dichotomy (`recall()` vs `search()`) exposed to users | Native single `query()` façade with deterministic auto-routing strategy | **Workstream A** (Memory) |
| **External Event Bus** | Pulse is internal. Agents have no way to react to swarm events | SSE/webhook adapter over Pulse for 9 canonical events | **Workstream C** (Coordination) |
| **Rejection API** | Guards throw inner exceptions or silent blocks | `OperationResult` (`AcceptanceResult` \| `RejectionResult`) union type | **Workstream B** (Verification) |
| **Dedup Predicate** | Legacy `valid_until IS NULL` in `check_dedup` | `is_tombstoned = 0` canonicalized across all storage components | **Workstream A** (Memory) |

---

## 3. Execution Roadmap

Execution is structured into three strict phases to prevent product drift. **Contract first, unification second, packaging third.**

### 3.1 Workstream A: Contract Stabilization (The Foundation)

Before adding any new features, we fix existing structural drifts and type definitions.

- [ ] **Fix 1:** Fix Dedup predicate drift in `store_mixin.py` (`valid_until` → `is_tombstoned`).
- [ ] **Fix 2:** Define `QueryInput` + `QueryResult` types (Pydantic models) in `cortex-sdk`.
- [ ] **Fix 3:** Define `RejectionResult` and `OperationResult` semantic types for guards.
- [ ] **Fix 4:** Define `HealthReport` type with explicit degradation vectors (e.g., L2 offline).
- [ ] **Fix 5:** Internally mark legacy v1 vote path in `consensus_manager.py` as deprecated.

### 3.2 Workstream B: Surface Unification (The DX Layer)

We expose the actual capabilities behind the unified contracts created in Workstream A.

- [ ] **Task 1:** Implement unified `query()` façade in SDK, mapping strategies (`auto`, `bayesian`, `hybrid`, etc.) to backend RPC calls.
- [ ] **Task 2:** Build Event Bus Adapter (SSE/callbacks) for 9 core coordination events (`agent.registered`, `fact.stored`, `taint.escalated`, etc.).
- [ ] **Task 3:** Implement Snapshot/Export functionality for L1 session working memory to make it portable.
- [ ] **Task 4:** Create a minimal Agent Heartbeat protocol for liveness verification during consensus.
- [ ] **Task 5:** Emit concrete `RecoveryReport` during `MemoryMixin` boot sequence instead of silent fallback.

### 3.3 Workstream C: Packaging Boundary (The Product)

Define the exact perimeter of what belongs to Open Core (Apache-2.0) vs Premium (BSL).

**Open Core Surface (Apache-2.0):**
- Persistence & SQLite Core
- `store`, `query`, `history`, `time_travel`
- Ledger verification
- Basic contradiction guards (FTS5 overlap)
- Tripartite Memory initialization

**Premium Surface (BSL):**
- WBFT Consensus (`byzantine.py`) & Reputation (`manager.py`)
- Persistent taint propagation DAG (`taint.py`)
- Advanced Immune Membrane (`membrane.py`)
- EU AI Act Article 12 Compliance exports (`tracker.py`)
- Graph-RAG enrichment & Semantic Compaction

*(Out of Scope for v1: Formal proofs / Z3, advanced multi-cloud scaling, deep swarm orchestration)*

---

## 4. Workstream Breakdown & Files Affected

| Workstream | Affected Files | Complexity |
|:---|:---|:---|
| **A. Stabilization** | `cortex/engine/store_mixin.py`, `cortex-sdk/models.py`, `cortex/consensus/manager.py` | Low |
| **B. Unification** | `cortex-sdk/client.py`, `cortex/routes/events.py` (new), `cortex/engine/memory_mixin.py` | Medium |
| **C. Packaging** | `open-cortex/router.py`, `open-cortex/persistence.py`, docs | Low |

---

## 5. Definition of Done (DoD)

The Gap Analysis & Build Plan phase is finished. The next stage is **Phase 4 - Implementation**, where we will execute Workstreams A, B, and C sequentially.

Success of Phase 4 is contingent on all `cortex-sdk` type hints compiling with `pyright`, existing functionality continuing to pass `pytest tests/`, and the API surface strictly matching the layout in `API-SURFACE.md`.
