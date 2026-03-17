---
description: RFC v0.1 Cortex-Persist Native AI Architecture — Frozen Normative Draft
---

# RFC-CORTEX-NATIVE-AI

## 0. Status

**Frozen Normative Draft v0.1** — 2026-03-14

> This document defines the operational ground truth for CORTEX-Persist cognitive hypervisor architecture.
> Mathematical formalizations pending proof are deferred to formal appendices (see §16).
> Sections are classified per RFC 2119: **MUST** (hard invariant), **SHOULD** (strong guidance),
> **TARGET** (performance SLO), **EXPERIMENTAL** (pending formal proof or validation).

## 1. Purpose

Define the normative architecture of Cortex-Persist as a sovereign cognitive hypervisor:
a decentralized, cryptographically verifiable, probabilistically weighted memory subsystem
for autonomous AI agent swarms.

## 2. Scope

This RFC standardizes the data structures, state machines, consensus bounds, API contracts,
and the rigorous Rust-first physical infrastructure required for the Swarm to operate a
mathematically verifiable, self-governing memory subsystem.

## 3. Non-Goals

This RFC explicitly does not guarantee:

- Metaphysical truth of all accepted beliefs.
- Full graph satisfiability at ingestion time.
- Real-time global logical closure.
- Byzantine-proof consensus across arbitrary hostile networks.
- Vector-space erasure guarantees after third-party model exposure.

## 4. Terminology

| Term | Classification | Definition |
|:-----|:---------------|:-----------|
| **MUST / MUST NOT** | Normative | Hard invariants. Structural violations cause a Hard Fault. Per RFC 2119. |
| **SHOULD / SHOULD NOT** | Normative | Strong implementation guidance. Deviation requires documented rationale. |
| **TARGET** | Performance | Performance SLO — operational objective, not formal guarantee. |
| **EXPERIMENTAL** | Pending | Subject to revision pending formal proof. See appendices. |
| **Belief Object (BO)** | Ontology | The atomic unit of probabilistically weighted cognition. |
| **Semantic CRDT** | Ontology | A CRDT guaranteeing eventual consistency via explicit logic dependency (`entails`/`discards`) rather than naive wall-clock timestamps (e.g. LWW). |
| **LogOP** | Ontology | Logarithmic Opinion Pool — the mandatory externally-Bayesian function for probabilistic belief consensus and fusion. |

## 5. System Model

The system acts as a decentralized hypervisor. Agents produce operational facts. The Memory
Scheduler dictates context injection using a multivariable tensor equation. The Consensus
protocol (Zenoh-based) propagates locally active belief states. Shared memory (iceoryx2)
provides lock-free IPC to downstream inference pipelines (vLLM/SGLang).

## 6. Data Model

```typescript
type BeliefState = "ACTIVE" | "CONTESTED" | "SUBSUMED" | "DISCARDED" | "ORPHANED";

interface ProvenanceEnvelope {
  source_hash: string;
  source_type: "agent" | "tool" | "human";
  tenant_id: string;
  signer_id: string;
  signature: string;
  created_at: string; // UUIDv7 embedded chronos
  was_generated_by: string; // PROV-AGENT episode ID
}

interface BeliefObject {
  belief_id: string; // UUIDv7
  proposition: string;
  semantic_embedding: Float32Array; // L2 vector projection
  state: BeliefState;
  confidence_score: number; // P(H|E) scalar value
  variance: number; // Ignorance quantification
  decay_rate: number; // Logarithmic epistemic fading
  provenance: ProvenanceEnvelope;
  relations: {
    entails: string[];   // Pre-conditions (BO IDs)
    discards: string[];  // Refuted claims (BO IDs)
  };
}
```

> [!NOTE]
> The `BeliefObject` schema is **MUST**-level normative. Field additions require RFC amendment.

## 7. Integrity Plane

> **Classification: MUST (Normative)**

The Integrity Plane governs provenance, tenant isolation, and cryptographic immutability.

### Requirements

- Every state change MUST be committed as an immutable event into a Sparse Merkle Tree (SMT) via models such as `mssmt`.
- A mutation MUST NOT overwrite a prior belief payload in place.
- Revisions MUST be represented as signed patches referencing the previous state.
- Every read path MUST verify ledger integrity, tenant binding, and signature validity.
- The `attest_lineage(artifact_id)` API MUST mathematically resolve execution proofs in $O(\log N)$ time using the local SMT root.

## 8. Belief Plane

> **Classification: MUST (Normative)**

A Belief Object is an accepted, suspended, or discarded unit of operational cognition bounded under explicit assumptions.

### Transitions

| Current State | Event | New State |
| ------------- | ----- | --------- |
| ACTIVE        | Critical contradiction         | CONTESTED          |
| ACTIVE        | Signed patch invalidating it   | DISCARDED          |
| ACTIVE        | Parent dependency invalidated  | ORPHANED           |
| CONTESTED     | Favorable LogOP adjudication   | ACTIVE             |
| ORPHANED      | Valid structural reconciliation| ACTIVE / DISCARDED |

### Invariant (MUST)

If a root dependency becomes invalid or refuted (via `discards`), dependent beliefs
MUST transition to non-operational state. The invalidation of the root reference itself
is executed in $O(1)$ via precomputed dependency indices; rehidratation and structural
reconciliation of the affected subgraph is performed as deferred work, not guaranteed
as constant-time.

> [!IMPORTANT]
> The $O(1)$ claim applies strictly to the root reference state change, not to the
> full downstream propagation. See Appendix ATMS §2 for formal propagation mathematics.

## 9. Swarm Sync & Consensus

> **Classification: MUST (Normative) — Formal mathematics: EXPERIMENTAL (see Appendix CRDT)**

Swarm synchronization is eventually convergent over Edge topologies, eschewing JVM
bottlenecks in favor of Rust-native messaging.

### Requirements (MUST)

- Transport MUST be orchestrated via **Zenoh** (L3/L4) to eliminate central broker latencies and provide multi-network pub/sub capabilities.
- Merge operations MUST be executed using the Semantic Conflict Model isolating $o_1 \parallel o_2$ collisions based on pre-conditions. LWW (Last-Writer-Wins) based purely on timestamps is STRICTLY PROHIBITED.
- Conflict Bayesian aggregation MUST use Logarithmic Opinion Pools (LogOP). Linear Opinion Pools (LinOP) are FORBIDDEN due to risk of multimodal probability flattening.

### Epistemic Veto (MUST)

A veto MUST NOT act as an unconditional probability-zero annihilator at ingestion time.
Vetoes introduce a saturating epistemic penalty validated by cryptographic proof, and
can only collapse to total exclusion ($P \to 0$) after one of:

1. **L3 Auditor review** confirming structural justification.
2. **Reinforced quorum** (≥ 2/3 of active swarm nodes concurring).

A single node MUST NOT unilaterally annihilate swarm consensus. The geometric LogOP
equation permits $P=0$ only when injected by an authorized supervisor with audit trail.

> [!WARNING]
> The formal algebraic constraints on LogOP veto saturation, tombstone semantics,
> and CRDT convergence proofs are **EXPERIMENTAL** and specified in
> [RFC-CORTEX-CRDT-MATH-APPENDIX](file:///.agents/specs/RFC-CORTEX-CRDT-MATH-APPENDIX.md).

### Tombstone Semantics (SHOULD)

When a Belief Object is discarded, a tombstone marker SHOULD be retained to maintain
causal consistency across replicas. Concurrent operations may reference the discarded BO;
premature removal would cause replica divergence. Tombstone garbage collection is
deferred to the Memory Consolidation pipeline (§12 Cold Resume).

## 10. Memory Scheduler

> **Classification: MUST (Normative)**

Context injection MUST strictly abide by the Memory Scheduler evaluation tensor, generating a `Context Package`:

$$ \text{Score}(m) = \frac{(\text{Rel} \cdot w_r) + (\text{Conf} \cdot w_c) + (\text{Rec} \cdot w_t)}{\text{Cost}_{\text{tokens}} + \text{Risk}_{\text{contam}}} $$

If $Risk_{\text{contam}}$ detects cascading structural contradictions unmitigated by available resolution bounds, the score MUST asymptotize to 0, completely rejecting the memory payload.

## 11. Core API

> **Classification: MUST (Normative)**

1. `ingest_episode(event_obj)`: Segregates sensory noise from immediate attention; archives directly to the Episodic L2 Log.
2. `revise_belief(belief_id, evidence_ref)`: Triggers Assumption-based Truth Maintenance (ATMS) and Bayesian recalibration. See [ATMS Appendix](file:///.agents/specs/RFC-CORTEX-ATMS-SEMANTICS.md).
3. `resolve_context(query_params)`: Evaluates the Memory Equation tensor to yield the active Context Package.
4. `attest_lineage(artifact_id)`: Generates ZK-ready cryptographic proofs of inferential origin tracing back to raw telemetry episodes.
5. `fork_memory(agent_id, context_delta)`: Instantiates isolated semantic sandboxes permitting complex Monte Carlo counterfactual simulations.

## 12. Resume Semantics & IPC

> **Classification: TARGET (Performance SLO)**

### Hot Resume

**TARGET: sub-10 ms** resume latency (~0 ms logical in same process/session).

MUST bypass TCP/Socket serialization completely. Requires POSIX Shared Memory (SHM)
operating underneath the lock-free Blackboard architectural pattern orchestrated via
**iceoryx2** for tensor ingestion.

> [!NOTE]
> "~0 ms" is a logical abstraction for in-process cache hit. The practical bound
> is sub-10 ms, governed by SHM page fault cost and iceoryx2 zero-copy overhead.

### Warm Resume

**TARGET: p95 < 200 ms** under nominal load (SLO, not ontological guarantee).

Context structures deterministically rehydrated from index. Performance degrades
gracefully under contention; hard failure threshold at p99 > 1s.

### Cold Resume

Boot from $G_c$ (Community Subgraph) consolidated axioms natively extracted via
background `Memory Consolidation Jobs` after episodic logs have been pruned.

## 13. Threat Model

> **Classification: MUST (Normative)**

| Threat | Defense | Classification |
|:-------|:--------|:---------------|
| **Semantic Poisoning** | Historical proof-of-expertise weightings in LogOP | MUST |
| **Biased Consensus** | Swarm diversity constraints + anomaly detection | MUST |
| **Network Partition** | Zenoh Semantic CRDT convergence without Master/DNS | MUST |
| **Malicious Veto** | Saturating penalty + L3 audit (see §9) | MUST |
| **Replay Attack** | Causal ordering + monotonic CRDT clocks | MUST |

> See [Epistemic Failure Modes](file:///.agents/tests/epistemic-failure-modes.md) for concrete test scenarios.

## 14. Performance Targets

> **Classification: TARGET (Performance SLO)**

| Metric | Target | Classification |
|:-------|:-------|:---------------|
| IPC Overhead | ZERO-COPY lock-free arrays | MUST |
| Local Cognitive Loop | < 10 ms | TARGET |
| Deep Adjudication | < 45 s | TARGET |
| Hot Resume | sub-10 ms | TARGET |
| Warm Resume | p95 < 200 ms nominal | TARGET |
| Serialized JSON/Pickle in critical path | FORBIDDEN | MUST |

## 15. Forbidden Simplifications

> **Classification: MUST NOT**

The following architectural shortcuts are structurally incompatible with this RFC:

1. **Memory RAG-only** — Retrieval-Augmented Generation without belief revision does not satisfy Axiom Ω₃ (Byzantine Default). RAG retrieves; it does not maintain truth.
2. **Vector similarity ≡ truth maintenance** — Cosine similarity measures geometric proximity, not logical entailment. A system that confuses embedding distance with epistemic certainty produces hallucination that survives retrieval.
3. **Mutable belief overwrite** — Direct overwrites of `BeliefObject.proposition` destroy the hash chain. Revisions MUST be expressed as signed patches.
4. **LWW (Last-Writer-Wins) timestamps** — Wall-clock ordering is neither causal nor monotonic. LWW is STRICTLY PROHIBITED for belief state resolution.
5. **Single-node veto annihilation** — A lone node MUST NOT collapse swarm consensus to $P=0$ without audit trail and quorum (see §9).

## 16. Formal Appendices (EXPERIMENTAL)

The following documents contain formal mathematical specifications pending complete proof.
They are referenced throughout this RFC and will be promoted to normative status upon
verification.

| Document | Scope | Status |
|:---------|:------|:-------|
| [RFC-CORTEX-CRDT-MATH-APPENDIX](file:///.agents/specs/RFC-CORTEX-CRDT-MATH-APPENDIX.md) | CRDT typology, merge semantics, LogOP veto algebra, tombstone GC, partition convergence | EXPERIMENTAL |
| [RFC-CORTEX-ATMS-SEMANTICS](file:///.agents/specs/RFC-CORTEX-ATMS-SEMANTICS.md) | Dependency indexing, assumption environments, propagation mathematics, backtracking | EXPERIMENTAL |
| [Epistemic Failure Modes](file:///.agents/tests/epistemic-failure-modes.md) | Adversarial test scenarios, invariant validation, acceptance criteria | Test Spec |

## 17. Open Questions

- Optimal heuristic embedding strategy for identifying $G_c$ abstractions without invoking excessive off-cycle LLM generation tasks?
- Upper latency bounds for asynchronous Zero-Knowledge Proof (ZKP) calculation when spanning an SMT root enclosing millions of active belief leaves?
- Formal verification of LogOP convergence under adversarial vote injection: does the saturating penalty converge or oscillate?
- Tombstone GC policy: time-based vs. consensus-acknowledgment-based purging?

---

*CORTEX-Persist · RFC v0.1 Frozen · 2026-03-14*
