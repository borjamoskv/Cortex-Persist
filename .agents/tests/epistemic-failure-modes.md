# Cortex-Persist: Epistemic Failure Modes Test Specifications

> **Status:** Test Specs v0.1
> **Parent RFC:** [RFC-CORTEX-NATIVE-AI v0.1](file:///.agents/workflows/RFC-CORTEX-NATIVE-AI.md)
> **Date:** 2026-03-14

---

## 0. Preamble

This document defines concrete adversarial and thermodynamic decay scenarios that
CORTEX-Persist MUST survive. Each scenario specifies trigger conditions, expected
system behavior, invariants under test, and acceptance criteria.

---

## FM-01: Malicious Veto

**Trigger:** Agent $j$ intentionally submits $P_j = 0$ (or $P_j \to \epsilon$) for a
belief that the majority of the swarm holds as `ACTIVE` with high confidence.

**Expected Behavior:**

1. The veto is accepted as $P_j = \epsilon$ (saturating penalty, not annihilation).
2. The fused LogOP probability decreases but does not collapse to 0.
3. Agent $j$'s `consensus_weight` is flagged for L3 audit.
4. If determined malicious: epistemic slashing applied ($w_j \leftarrow w_j \cdot \alpha^{-k}$).

**Invariant:** No single agent can unilaterally collapse swarm consensus.

**Acceptance Criteria:**
- [ ] $P_{\text{LogOP}} > 0$ after single-agent veto without L3 confirmation.
- [ ] Audit trail records veto event with agent identity, timestamp, and justification hash.
- [ ] Slashing coefficient applied within 1 consolidation cycle after malice determination.

---

## FM-02: Causal Cycle

**Trigger:** Chain $A \vdash B \vdash C \vdash \neg A$ introduced via concurrent operations.

**Expected Behavior:**

1. ATMS cycle detection fires during `entails`/`discards` assertion.
2. All nodes in the cycle transition to `CONTESTED`.
3. The cycle is escalated to Tribunal (LogOP adjudication).
4. The weakest edge (lowest `confidence_score`) is severed.

**Invariant:** No circular dependency survives in the committed belief graph.

**Acceptance Criteria:**
- [ ] Cycle detected within $O(|E|)$ of the light cone.
- [ ] No `ACTIVE` beliefs remain with circular dependencies after resolution.
- [ ] Tribunal event logged with full causal chain.

---

## FM-03: Belief Orphaning (Root Revocation)

**Trigger:** A root assumption $a$ is explicitly revoked via signed patch.

**Expected Behavior:**

1. Root reference marked invalid in $O(1)$ (index flag).
2. Immediate children transition to `ORPHANED`.
3. Deferred subgraph evaluation begins in next consolidation cycle.
4. Children with alternative justifications are reconciled to `ACTIVE`.
5. Children without alternatives transition to `DISCARDED`.

**Invariant:** No belief with an invalidated root chain remains `ACTIVE`.

**Acceptance Criteria:**
- [ ] Root invalidation completes in < 1 ms.
- [ ] All orphaned nodes resolved within 1 consolidation cycle.
- [ ] Reconciled nodes have valid, non-circular justification chains.

---

## FM-04: Source Hash Collision

**Trigger:** Two distinct `ProvenanceEnvelope`s from different tenants produce
identical `source_hash` values.

**Expected Behavior:**

1. SMT insertion detects the collision during Merkle proof generation.
2. The second envelope is rejected at the gate layer.
3. An integrity alert is raised (P0 — potential cryptographic weakness).
4. Both envelopes are preserved in quarantine for forensic analysis.

**Invariant:** No two distinct provenance records share an SMT leaf.

**Acceptance Criteria:**
- [ ] Collision detected before belief state mutation.
- [ ] No data loss — both envelopes preserved.
- [ ] P0 alert emitted with collision details.

---

## FM-05: Tenant Key Destruction (GDPR Right-to-be-Forgotten)

**Trigger:** GDPR erasure request for tenant $t$.

**Expected Behavior:**

1. AES-256 master key for tenant $t$ is cryptographically destroyed.
2. All ciphertext for tenant $t$ becomes functionally random (irreversible).
3. ZK proofs of unlinking are generated, demonstrating that:
   - The key material no longer exists in any keyring.
   - The ciphertext cannot be decrypted.
4. SMT leaves for tenant $t$ are replaced with tombstone markers.
5. Provenance references across other tenants are preserved (cross-references
   point to tombstones, not dangling pointers).

**Invariant:** Post-destruction, no computational method can reconstruct tenant data.

**Acceptance Criteria:**
- [ ] Key destruction confirmed by keyring audit (no backup copies).
- [ ] ZK proof of unlinking validates successfully against SMT root.
- [ ] Cross-tenant references resolve to tombstones without errors.
- [ ] EU AI Act audit trail records the erasure event immutably.

---

## FM-06: Replay Attack on Patches

**Trigger:** Attacker resubmits a previously valid but now obsolete `BeliefPatch`.

**Expected Behavior:**

1. The patch's `parent_hash` is checked against the current patch DAG.
2. If the parent hash corresponds to a superseded state, the patch is rejected.
3. Monotonic CRDT clocks confirm the patch timestamp is stale.
4. The replay attempt is logged as a security event.

**Invariant:** No obsolete patch can modify current belief state.

**Acceptance Criteria:**
- [ ] Replay rejected at ingestion layer, before any state mutation.
- [ ] Security event logged with attacker metadata (if available).
- [ ] No state regression occurs.

---

## FM-07: Network Partition Divergence

**Trigger:** Network partition splits the swarm into $G_1$ and $G_2$ for > 1 hour.
Both partitions continue accepting writes to the same `BeliefObject`.

**Expected Behavior:**

1. Both partitions operate independently (AP-mode).
2. Upon partition heal, CRDT merge executes per Appendix CRDT §2.1.
3. Concurrent conflicting state transitions are resolved via MV-Register + LogOP.
4. Post-merge state is identical regardless of merge order (commutativity).
5. No data loss — all operations from both partitions are preserved.

**Invariant:** Post-heal state satisfies SEC (Strong Eventual Consistency).

**Acceptance Criteria:**
- [ ] All operations from both partitions present in merged state.
- [ ] Merge produces identical result in both directions ($G_1 \sqcup G_2 = G_2 \sqcup G_1$).
- [ ] No `ORPHANED` beliefs resulting from merge artifacts.

---

## FM-08: Tombstone Premature GC

**Trigger:** Tombstone for a `DISCARDED` BO is garbage-collected before all
replicas have acknowledged it.

**Expected Behavior:**

1. A replica that hasn't received the tombstone still holds the BO as `ACTIVE`.
2. The replica sends an operation referencing the "undead" BO.
3. The receiving replica detects the tombstone-less reference and:
   - Requests tombstone resync from peers.
   - Blocks the operation until consistency is restored.

**Invariant:** Premature tombstone GC MUST NOT cause permanent replica divergence.

**Acceptance Criteria:**
- [ ] Divergence detected within 1 sync cycle.
- [ ] Tombstone resync completes without data loss.
- [ ] Alert raised for tombstone GC policy violation.

---

## FM-09: Epistemic Cascade Failure

**Trigger:** A high-confidence root belief (C5, used by 100+ dependent beliefs)
is invalidated by new evidence.

**Expected Behavior:**

1. Root invalidated in $O(1)$ (index flag).
2. Deferred propagation scheduled — not blocking the real-time cognitive loop.
3. Dependent beliefs processed in batches by the Memory Consolidation pipeline.
4. System remains operational during cascade — new queries receive a degraded
   but consistent context package (with contamination risk flag elevated).

**Invariant:** Cascade invalidation MUST NOT block the real-time cognitive loop (< 10 ms).

**Acceptance Criteria:**
- [ ] Real-time loop continues operating within TARGET latency during cascade.
- [ ] All dependent beliefs resolved within 3 consolidation cycles.
- [ ] Memory Scheduler's $Risk_{\text{contam}}$ correctly flags affected contexts.

---

*CORTEX-Persist · Epistemic Failure Modes v0.1 · Test Specs · 2026-03-14*
