# RFC 02: CORTEX Security Architecture & Epistemic Control Plane (Spec)

**Title:** Verifiable State Transition Control under Uncertainty
**Status:** Architecture Draft
**Date:** March 17, 2026

---

## 1. Abstract

CORTEX separates security into four distinct but interdependent planes. This specification formally defines the invariants, capabilities, risk tiers, and threat models necessary to maintain long-term operational continuity under controlled degradation, shifting the focus from generation to verification.

## 2. Four Planes of Security

- **A. Execution Security (System Layer):** Protection of host resources, tool execution scopes, network egress, filesystem limits, and secret isolation.
- **B. Epistemic Security (Generation Layer):** Governance over the ontological status of LLM outputs, preventing hypotheses from acquiring operational reality without validation.
- **C. State Integrity (Persistence Layer):** Cryptographic auditing, causal linking, taint propagation, and deterministic reversal of system mutations.
- **D. Operational Sovereignty (Agency Layer):** The rules of engagement enabling autonomous action within bounded friction environments.

---

## 3. Strict Security Invariants

### Invariant 1: No Direct Generative Mutation
No generative output may mutate persistent state or trigger side effects without traversing:
1. Structural Validation (Strict Schema / AST Check)
2. Policy Validation (RBAC, Scopes, Bounds)
3. Causal Validation (Provenance & Dependency check)
4. Cryptographic Auditing (Ledger persistence)

### Invariant 2: Provenance Before Persistence
Every persisted artifact, action, or state change MUST include:
- `source_id` (Actuating Agent / Model)
- `parent_id` (Causal linkage to prior fact/decision)
- `timestamp`
- `confidence_class`
- `verification_status`

### Invariant 3: Deterministic Taint Propagation
If node $N$ is marked invalidated or corrupted, all nodes in its descendant causal DAG ($D_{N}$) MUST automatically be:
- Degraded in `confidence_class`
- Tainted (marked for quarantine)
- Isolated from downstream querying
- Scheduled for re-verification

### Invariant 4: Capability-Bound Execution
No agent may execute a kinetic action outside of its cryptographic or formal:
- Bounded Role Definition
- Authorized Scope (Resource restrictions)
- Time-to-Live (TTL / Temporal Window)
- Allowed Risk Tier (See Section 4)

### Invariant 5: Failure Locality
All failures MUST abort locally before mutating global state. A failure in generative formatting, policy breach, or validation must explicitly halt execution without escalation to global memory or cross-agent consensus.

---

## 4. Risk-Tiered Execution Model

All operational behaviors are bucketed by thermodynamic and operational cost.

| Tier | Name | Target Action | Constraints / Gates |
|---|---|---|---|
| **Tier 0** | Read-Only Cognition | Summarization, query parsing, classification, planning (no side effects). | Epistemic validation; fast execution; no persistence. |
| **Tier 1** | Reversible Local Writes | Temporary caching, scratchpad updates, output drafting. | Local capability scope; TTL eviction. |
| **Tier 2** | Persistent Internal State | CORTEX Ledger writes, knowledge crystallization, memory updates. | Invariants 1 & 2 applied; Cryptographic hash chain updated. |
| **Tier 3** | External Side Effects | Tool use, email dispatch, config updates, non-critical API requests. | Invariant 4 enforced. Required capability signature. |
| **Tier 4** | Irreversible / Critical | Production deployment, financial transactions, credentials, destructive modifications. | Two-Phase Commit; Explicit Human Consensus or Hardware-Level Gate required. |

---

## 5. Threat Model

CORTEX actively mitigates the following threat classes.

### Threat Class A: Generative Faults (Internal Entropy)
- **Vectors:** Schema drift, hallucinated payloads, invalid tool arguments, fabricated provenance, state inconsistency under loop pressure.
- **Mitigation:** Invariant 1 (No Direct Generative Mutation), Invariant 5 (Failure Locality).

### Threat Class B: Instruction Attacks (Injection)
- **Vectors:** Prompt injection via external data, malicious intent hijacking, policy confusion.
- **Mitigation:** Capability Scopes restrict blast radius. Intent is structurally bound to signed capability.

### Threat Class C: Runtime Attacks (Classic System Exploits)
- **Vectors:** Arbitrary file writes, sandbox escape, shell abuse, rogue dependency execution, SSRF.
- **Mitigation:** Execution Security (Plane A). Robust containerization, process sandboxing, egress limits. Traceability aids forensics but does not stop escape.

### Threat Class D: Persistence Attacks
- **Vectors:** Tainted memory inheritance, corrupt writes, orphaned logic ("Ghosts"), false consensus solidified by multi-agent echo chambers.
- **Mitigation:** Invariant 2 & 3. Taint tracking explicitly isolates corrupt branches.

### Threat Class E: Governance Failure
- **Vectors:** Over-broad permissions leading to high-impact automation failure, role drift, irreversible autonomous damage.
- **Mitigation:** Risk Tiers (Section 4) bound automated actions to Tier 0-2 unconditionally, demanding specific grants for Tiers 3-4.

---

## 6. Persistence Semantics & Consensus

- **Immutability vs State Correctness:** The CORTEX Ledger is append-only and immutable. If an incorrect state is committed, the hashes prove who committed what, and when. State correction is handled via **Supersession Semantics** (a new fact supersedes the old) while maintaining the original forensic trail.
- **Consensus does not equal Truth:** If a 5-agent swarm achieves 100% consensus on a fact, the system tags the confidence high but STILL records it as probabilistic conjecture until it crosses an empirical validation test. 

---
*CORTEX Security Spec v1 - Approved for implementation in System Gates.*
