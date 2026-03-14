---
description: RFC v0.1 Cortex-Persist Native AI Architecture
---

# RFC v0.1: Cortex-Persist Native AI Architecture

> **Status:** Normative Draft  
> **Axiom:** Ω₃ (Verify then trust)

## 1. Implementation Maturity

This RFC defines the normative architecture and system invariants of Cortex-Persist Native AI.
Some subcomponents remain under formal specification and are therefore treated as implementation-bound appendices rather than blocking dependencies:

- CRDT merge algebra for semantic swarm sync (`RFC-CORTEX-CRDT-MATH-APPENDIX.md`)
- LogOP veto saturation rules (`RFC-CORTEX-CRDT-MATH-APPENDIX.md`)
- ATMS dependency indexing formalism (`RFC-CORTEX-ATMS-SEMANTICS.md`)
- Resume-path service level objectives under load

## 2. Terminology

- **MUST / MUST NOT**: Hard invariants. Structural violations of these will cause a Hard Fault.
- **SHOULD / SHOULD NOT**: Strong implementation guidance.
- **TARGET**: Performance SLO, not formal guarantee.
- **EXPERIMENTAL**: Subject to revision pending formal proof or benchmark evidence.

## 3. Architecture Planes

### 3.1. Integrity Plane (Plano de Integridad Criptográfica)
**Guarantee:** No data enters the operative light cone without demonstrable provenance.

- **MUST**: Each episodic or semantic transaction MUST be sealed in a Sparse Merkle Tree (SMT) interconnected with the Master Ledger.
- **MUST NOT**: Belief modification MUST NOT overwrite its original vector. It MUST fork the tree branch, emitting an immutable `BeliefPatch` signed by the originating agent (`PROV-AGENT`).
- **MUST**: If the ledger hash chain fractures or the `tenant_id` fails cryptographic validation, the read operation MUST collapse with a Hard Fault at $t=0$, isolating contamination before it reaches the LLM.

### 3.2. Belief Plane (Plano de Creencias y Mantenimiento de Verdad)
**Guarantee:** Active memory is a logically coherent subgraph, not a bag of semantically noisy vectors.

- **MUST**: Each Belief Object (`BO`) MUST operate with explicit causal relations (`entails`, `discards`) and an epistemic state (Active, Suspended, Discarded).
- **SHOULD**: The Inconsistency Tribunal (DeepThinK Gatekeeper). If a collision generates a critical `consensus_weight` differential, the hypervisor SHOULD `SUSPEND` the subgraph and route exclusively to Heavy Reasoning (System 2, e.g., Gemini 3.1 DeepThinK). The LLM returns the exact deductive trace, crystallizing as a new Axiom.
- **MUST**: Cascading Invalidation. Root invalidation MUST propagate via precomputed indexed invalidation, allowing state change in constant time by reference and deferred local rehydration of the affected subgraph.

### 3.3. Swarm Sync (Sincronización de Enjambre)
**Guarantee:** Topological convergence does not depend on central validation.

- **MUST**: Tactical execution agents MUST synchronize non-blocking memory via a P2P bus (Zenoh) utilizing Semantic CRDTs.
- **MUST**: LogOP Consensus (Epistemic Veto). Vetoes DO NOT operate as absolute zero directly in the tactical layer; they MUST introduce a saturating epistemic penalty validated by proof, and can only collapse to total exclusion after L3 audit or reinforced quorum.
- **SHOULD**: Thermal Isolation (iceoryx2). Shared embedding tensors SHOULD reside in zero-copy memory (SHM) to allow Python agents to consume state instantaneously without serialization overhead.

### 3.4. Resume Paths (Colapso y Expansión de Contexto)
**Guarantee:** Deterministic state recovery across temporal bounds.

- **TARGET (Hot Resume)**: ~0 ms logical / sub-10 ms practical within the same resident process or session via KV-Cache Persistence.
- **TARGET (Warm Resume)**: p95 < 200 ms under nominal load and bounded indexed cardinality. Extracts state from indexed storage and asynchronously reconstructs adjacent causal light cones.
- **MUST (Cold Resume)**: NightShift / Crystallization. Raw episodic logs MUST NOT survive a Cold Boot. The system MUST compact daily episodic noise into clean modular rules. At cold boot, the system MUST only load Axioms (maximum Shannon compressed entropy).

### 3.5. Compliance Plane (Membrana Regulatoria)
**Guarantee:** Deep auditability and structural compliance (e.g., EU AI Act Article 12).

- **MUST**: Every inference cycle modifying the Belief Plane MUST emit an immutable provenance certificate (VEX & PROV-O native).
- **MUST**: Zero-Knowledge Crypto-Shredding. GDPR "Right to be Forgotten" MUST physically destroy the AES key of the specific Tenant, cryptographically discarding the Layer 0 (plaintext), and proving unlinking via ZK-Proofs.

## 4. Failure Modes & Invariants

| Failure Mode | Structural Condition | Resolution (Invariant) |
| :--- | :--- | :--- |
| **Denial of Truth (Veto Attack)** | Compromised agent transmits a veto ($P=0$) blocking LogOP consensus. | **Epistemic Slashing**: Veto requires proof-of-work. False positives geometrically destroy the node's `consensus_weight` and trigger `immune-chaos` isolation. |
| **ATMS NP-Hard Explosion** | Full logical satisfiability evaluation of $10^6$ beliefs degrades to polynomial collapse. | **Light Cone Restriction**: ATMS restricts recalculation to $d \le 2$. Full re-balancing is deferred to background consolidation (NightShift/Sleep Cycle). |
| **Circular Epistemic Regression** | LLM assimilates its own processed logs as novel evidence to reaffirm false conclusions. | **Provenance Check**: `BO` merges MUST originate from orthogonal source hashes, structurally breaking the hallucination feedback loop. |

## 5. Forbidden Simplifications

- **RAG-only memory is non-compliant with Axiom Ω₃.**
- **Vector similarity is NOT truth maintenance.**
- **Mutable overwrite of belief state is FORBIDDEN.**
