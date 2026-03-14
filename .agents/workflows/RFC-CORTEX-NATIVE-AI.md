---
description: RFC v0.1 Cortex-Persist Native AI Architecture
---

# RFC-CORTEX-NATIVE-AI

## 0. Status
Normative Draft v0.1

## 1. Purpose
Define the normative architecture of Cortex-Persist as a sovereign cognitive hypervisor.

This RFC standardizes the transition of Cortex-Persist from passive vector retrieval to an active memory governance system. The system does not treat semantic similarity as sufficient evidence of validity. Instead, it separates three concerns that are commonly collapsed in RAG systems:
1. Cryptographic integrity of stored artifacts,
2. Epistemic status of active beliefs,
3. Distributed convergence of agent-local state.

The guiding invariant is Axiom Ω₃: *Verify then trust*. No datum may enter the operational context of a model unless its provenance, tenant binding, and structural validity can be mechanically verified.

## 2. Scope
This RFC standardizes the data structures, state machines, consensus bounds, and integrity checks required for the Swarm to operate a mathematically verifiable, self-governing memory subsystem.

## 3. Non-Goals
This RFC explicitly does not guarantee:
- Metaphysical truth of all accepted beliefs,
- Full graph satisfiability at ingestion time,
- Real-time global logical closure,
- Byzantine-proof consensus across arbitrary hostile networks,
- Vector-space erasure guarantees after third-party model exposure.

## 4. Terminology
- **MUST / MUST NOT**: Hard invariants. Structural violations of these will cause a Hard Fault.
- **SHOULD / SHOULD NOT**: Strong implementation guidance.
- **TARGET**: Performance SLO, not formal guarantee.
- **EXPERIMENTAL**: Subject to revision pending formal proof or benchmark evidence.

## 5. System Model
Components, trust boundaries, and execution model. The system acts as a decentralized hypervisor. Agents produce operational facts. The ATMS evaluates logic dependencies. The Consensus protocol propagates locally active belief states.

## 6. Data Model

```typescript
type BeliefState = "ACTIVE" | "SUSPENDED" | "DISCARDED" | "ORPHANED";

interface ProvenanceEnvelope {
  source_hash: string;
  source_type: string;
  tenant_id: string;
  signer_id: string;
  signature: string;
  created_at: string;
}

interface BeliefObject {
  belief_id: string;
  content_hash: string;
  state: BeliefState;
  consensus_weight: number;
  assumptions: string[];
  provenance: ProvenanceEnvelope;
  parents: string[];
  relations: Array<{
    type: "entails" | "discards" | "depends_on" | "supersedes";
    target_id: string;
  }>;
}
```

## 7. Integrity Plane

The Integrity Plane governs provenance, tenant isolation, and append-only mutation semantics.

### Requirements

- Every episodic or semantic write MUST be committed as an immutable event into a Sparse Merkle Tree linked to the Master Ledger.
- A mutation MUST NOT overwrite a prior belief payload in place.
- Any revision MUST be represented as a signed `BeliefPatch` referencing the previous belief state.
- Every read path MUST verify:
  - ledger integrity,
  - tenant binding,
  - signature validity,
  - patch ancestry.

If any of these checks fail, the request MUST terminate before model invocation.

## 8. Belief Plane

A Belief Object (BO) is not treated as globally true or false. It is treated as an accepted, suspended, or discarded unit of operational cognition under explicit assumptions.

### Invariant

If a root dependency becomes invalid, dependent beliefs MUST become non-operational immediately by index-based invalidation. Graph-wide reconciliation MAY be deferred.

### State Transitions

| Current State | Event | New State |
| ------------- | ----- | --------- |
| ACTIVE        | Critical contradiction         | SUSPENDED          |
| ACTIVE        | Signed patch invalidating it   | DISCARDED          |
| ACTIVE        | Parent dependency invalidated  | ORPHANED           |
| SUSPENDED     | Favorable adjudication         | ACTIVE             |
| ORPHANED      | Valid structural reconciliation| ACTIVE / DISCARDED |

### Conflict Escalation

If two or more active beliefs produce a contradiction whose weighted divergence exceeds a configured threshold, the affected subgraph MUST be suspended from default model access.

Resolution MUST be delegated to a high-reasoning adjudication path.
The adjudicator output MUST include:
- conflict inputs,
- assumptions used,
- deduction trace,
- resulting patch or axiom.

No resolved belief may re-enter ACTIVE state without a new signed artifact.

## 9. Swarm Sync

Swarm synchronization is eventually convergent and does not rely on a single central validator for tactical state propagation.

### Requirements

- Agent-local semantic state MUST be represented by CRDT-compatible data structures.
- Merge operations MUST be associative, commutative, and idempotent.
- Transport is orthogonal to merge semantics.
- Shared embeddings MAY be distributed through zero-copy shared memory where locality permits, but SHM is an optimization, not a correctness dependency.

### Epistemic Veto

A veto MUST NOT act as an unconditional probability-zero annihilator at ingestion time.

Instead, a veto introduces a signed negative evidence event with bounded suppression power.
Escalation to full exclusion requires one of:
- quorum reinforcement,
- adjudicated proof,
- L3 audit confirmation.

## 10. Resume Semantics

### Hot Resume
Re-entry into an already resident execution context without reconstructing model-local short-term state.
TARGET: sub-10 ms resume latency under same-process residency.

### Warm Resume
Reconstruction of task-adjacent cognitive state from indexed persistence without full semantic consolidation.
TARGET: p95 < 200 ms under nominal load.

### Cold Resume
Boot from consolidated axioms and compressed long-range semantic artifacts after raw episodic logs have been compacted or discarded.

## 11. Compliance Plane

- Every inference cycle modifying the Belief Plane MUST emit an immutable provenance certificate (VEX & PROV-O native).
- Zero-Knowledge Crypto-Shredding: GDPR "Right to be Forgotten" MUST physically destroy the AES key of the specific Tenant, cryptographically discarding the Layer 0 (plaintext), and proving unlinking via ZK-Proofs.

## 12. Threat Model

- **Malicious/Compromised Node**: Agents that sign coherent but contradictory patches to paralyze LogOP state.
- **Replay Attacks**: Agents broadcasting obsolete but properly signed patches.
- **Key Compromise / Tenant Bleed**: Valid signature but compromised backend keys.
- **Network Partition**: Divergent Swarm states due to edge disconnections.
- **Semantic Poisoning**: Slow degradation of axioms through coordinated injection over time.
- **Biased Consensus**: Correlated nodes amplifying a false consensus to brute-force a veto.

## 13. Failure Modes
Mechanical responses to structural failures are documented in `.agents/tests/epistemic-failure-modes.md`.

## 14. Performance Targets

- **Local Cognitive Loop**: Target local memory resolution bounded under 10 ms.
- **Deep Adjudication**: Heavy reasoning paths handled out-of-band bounded under 45 s.

## 15. Open Questions

- Can veto suppression be safely modeled as bounded log-odds decay instead of hard exclusion?
- Which CRDT family best fits belief dependency metadata without excessive tombstone growth?
- How should suspended subgraphs be serialized for audit without leaking sensitive tenant-level content?
- What is the minimal indexing scheme required for constant-time invalidation by dependency root?
