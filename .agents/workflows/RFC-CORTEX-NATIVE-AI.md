---
description: RFC v0.2 Cortex-Persist Native AI Architecture
---

# RFC-CORTEX-NATIVE-AI

## 0. Status
Normative Draft v0.2

## 1. Purpose
Define the normative architecture of Cortex-Persist as a sovereign cognitive hypervisor.

## 2. Scope
This RFC standardizes the data structures, state machines, consensus bounds, API contracts, and the rigorous Rust-first physical infrastructure required for the Swarm to operate a mathematically verifiable, self-governing memory subsystem.

## 3. Non-Goals
This RFC explicitly does not guarantee:
- metaphysical truth of all accepted beliefs,
- full graph satisfiability at ingestion time,
- real-time global logical closure,
- Byzantine-proof consensus across arbitrary hostile networks,
- vector-space erasure guarantees after third-party model exposure.

## 4. Terminology
- **MUST / MUST NOT**: Hard invariants. Structural violations cause a Hard Fault.
- **SHOULD / SHOULD NOT**: Strong implementation guidance.
- **TARGET**: Performance SLO, not formal guarantee.
- **EXPERIMENTAL**: Subject to revision pending formal proof.
- **Belief Object (BO)**: The atomic unit of probabilistically weighted cognition.
- **Semantic CRDT**: A CRDT that guarantees eventual consistency using explicit logic dependency (`entails`/`discards`) rather than naive wall-clock timestamps (e.g. LWW).
- **LogOP (Logarithmic Opinion Pool)**: The mandatory mathematically externally-Bayesian function used for probabilistic belief consensus and fusion.

## 5. System Model
The system acts as a decentralized hypervisor. Agents produce operational facts. The Memory Scheduler dictates context injection using a multivariable tensor equation. The Consensus protocol (Zenoh-based) propagates locally active belief states. Shared memory (iceoryx2) provides lock-free IPC to downstream inference pipelines (vLLM/SGLang).

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

## 7. Integrity Plane

The Integrity Plane governs provenance, tenant isolation, and cryptographic immutability.

### Requirements

- Every state change MUST be committed as an immutable event into a Sparse Merkle Tree (SMT) via models such as `mssmt`.
- A mutation MUST NOT overwrite a prior belief payload in place.
- Revisions MUST be represented as signed patches referencing the previous state.
- Every read path MUST verify ledger integrity, tenant binding, and signature validity.
- The `attest_lineage(artifact_id)` API MUST mathematically resolve execution proofs in $O(\log N)$ time using the local SMT root.

## 8. Belief Plane

A Belief Object is an accepted, suspended, or discarded unit of operational cognition bounded under explicit assumptions.

### Transitions
| Current State | Event | New State |
| ------------- | ----- | --------- |
| ACTIVE        | Critical contradiction         | CONTESTED          |
| ACTIVE        | Signed patch invalidating it   | DISCARDED          |
| ACTIVE        | Parent dependency invalidated  | ORPHANED           |
| CONTESTED     | Favorable LogOP adjudication   | ACTIVE             |
| ORPHANED      | Valid structural reconciliation| ACTIVE / DISCARDED |

### Invariant
If a root dependency becomes invalid or refuted (via `discards`), dependent beliefs MUST become non-operational immediately through recursive validation.

## 9. Swarm Sync & Consensus

Swarm synchronization is eventually convergent over Edge topologies, eschewing JVM bottlenecks in favor of Rust-native messaging.

### Requirements
- Transport MUST be orchestrated via **Zenoh** (L3/L4) to eliminate central broker latencies and provide multi-network pub/sub capabilities. 
- Merge operations MUST be executed using the Semantic Conflict Model isolating $o_1 \parallel o_2$ collisions based on pre-conditions. LWW (Last-Writer-Wins) based purely on timestamps is STRICTLY PROHIBITED.
- Conflict Bayesian aggregation MUST use Logarithmic Opinion Pools (LogOP). Linear Opinion Pools (LinOP) are FORBIDDEN due to risk of multimodal probability flattening.

### Epistemic Veto
A veto MUST NOT act as an unconditional probability-zero annihilator at ingestion time unless explicitly executed by an authorized supervising system. A specific $P=0$ assigned by a supervisor inside the geometric LogOP equation strictly collapses the swarm consensus to exactly 0, preventing probabilistic hallucination.

## 10. Memory Scheduler

Context injection MUST strictly abide by the Memory Scheduler evaluation tensor, generating a `Context Package`:
$$ \text{Score}(m) = \frac{(\text{Rel} \cdot w_r) + (\text{Conf} \cdot w_c) + (\text{Rec} \cdot w_t)}{\text{Cost}_{\text{tokens}} + \text{Risk}_{\text{contam}}} $$

If $Risk_{\text{contam}}$ detects cascading structural contradictions unmitigated by available resolution bounds, the score MUST asymptotize to 0, completely rejecting the memory payload.

## 11. Core API

1. `ingest_episode(event_obj)`: Segregates sensory noise from immediate attention; archives directly to the Episodic L2 Log.
2. `revise_belief(belief_id, evidence_ref)`: Triggers Assumption-based Truth Maintenance (ATMS) and Bayesian recalibration.
3. `resolve_context(query_params)`: Evaluates the Memory Equation tensor to yield the active Context Package.
4. `attest_lineage(artifact_id)`: Generates ZK-ready cryptographic proofs of inferential origin tracing back to raw telemetry episodes.
5. `fork_memory(agent_id, context_delta)`: Instantiates isolated semantic sandboxes permitting complex Monte Carlo counterfactual simulations.

## 12. Resume Semantics & IPC

### Hot Resume
TARGET: sub-10 ms resume latency.
MUST bypass TCP/Socket serialization completely. Requires POSIX Shared Memory (SHM) operating underneath the lock-free Blackboard architectural pattern orchestrated via **iceoryx2** for tensor ingestion.

### Warm Resume
TARGET: p95 < 200 ms under nominal load. Context structures deterministically rehydrated from index.

### Cold Resume
Boot from $G_c$ (Community Subgraph) consolidated axioms natively extracted via background `Memory Consolidation Jobs` after episodic logs have been pruned.

## 13. Threat Model
- **Semantic Poisoning**: Slow degradation of axioms through coordinated injection. Defended dynamically via historical proof-of-expertise weightings in LogOP.
- **Biased Consensus**: Correlated nodes amplifying a false consensus.
- **Network Partition**: Divergent Edge Swarm states. Handled flawlessly by Zenoh Semantic CRDT convergence without relying on Master/DNS indexers.

## 14. Performance Targets
- **IPC Overhead**: ZERO-COPY lock-free arrays. Serialized JSON/Pickle transmission is FORBIDDEN in the immediate semantic critical path.
- **Local Cognitive Loop**: < 10 ms.
- **Deep Adjudication**: < 45 s.

## 15. Open Questions
- Optimal heuristic embedding strategy for identifying $G_c$ abstractions without invoking excessive off-cycle LLM generation tasks?
- Upper latency bounds for asynchronous Zero-Knowledge Proof (ZKP) calculation when spanning an SMT root enclosing millions of active belief leaves?
