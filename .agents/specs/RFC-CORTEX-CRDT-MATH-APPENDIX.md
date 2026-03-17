# Appendix: Cortex-Persist CRDT Merge Semantics

> **Status:** EXPERIMENTAL — Living Formal Appendix  
> **Parent RFC:** [RFC-CORTEX-NATIVE-AI v0.1](file:///.agents/workflows/RFC-CORTEX-NATIVE-AI.md)  
> **Last Updated:** 2026-03-14

---

## 0. Preamble

This appendix formalizes the algebraic properties, merge semantics, and convergence guarantees required for Cortex-Persist Semantic Swarm Sync. All merge operations MUST satisfy the Strong Eventual Consistency (SEC) contract: replicas that have received the same set of updates — regardless of order — MUST converge to identical states without coordination.

**Foundational Axiom (SEC):** For any two replicas $r_i, r_j$ that have delivered the same set of operations $O$:
$$\text{state}(r_i) = \text{state}(r_j)$$

This requires all merge functions to be **commutative**, **associative**, and **idempotent** (a join-semilattice).

---

## 1. Entity CRDT Typology

Each entity in the Cortex-Persist data model maps to a specific CRDT class. The choice is driven by the entity's mutation semantics.

| Entity | CRDT Class | Lattice Join (⊔) | Rationale |
| ------ | ---------- | ----------------- | --------- |
| `BeliefObject.state` | MV-Register (Multi-Value) | Union of concurrent values; LogOP adjudicates | States can be concurrently contested; semantic resolution required |
| `BeliefObject.confidence_score` | Max-Register | $\max(a, b)$ | Confidence monotonically increases toward consensus; decreases require explicit `revise_belief` patches |
| `BeliefObject.relations.entails` | OR-Set (Observed-Remove) | Add-wins with causal context | Dependencies can be added/removed concurrently; additions win to preserve safety |
| `BeliefObject.relations.discards` | OR-Set (Observed-Remove) | Add-wins with causal context | Refutations are safety-critical; add-wins prevents silent un-refutation |
| `ProvenanceEnvelope` | Immutable (G-Set) | Union | Provenance is append-only; no mutation or deletion permitted |
| `BeliefPatch` | G-Set (Grow-only) | Union | Patches are immutable signed events; append-only log |

### 1.1 Lattice Structure

For each CRDT type $T$, the state space $(S_T, \sqsubseteq_T, \sqcup_T)$ forms a join-semilattice:

- **Partial order** $\sqsubseteq$: $a \sqsubseteq b \iff a \sqcup b = b$
- **Join** $\sqcup$: Least upper bound. $\forall a, b \in S: a \sqcup b \in S$
- **Bottom** $\bot$: The empty/initial state

**Monotonicity Invariant (MI-1):** For any operation $op$ applied to state $s$:
$$s \sqsubseteq \text{apply}(s, op)$$

State can only grow in the lattice. This guarantees convergence.

---

## 2. Merge Semantics

### 2.1 Algebraic Requirements

For any merge function $m: S \times S \to S$:

| Property | Definition | Consequence |
| -------- | ---------- | ----------- |
| **Commutativity** | $m(a, b) = m(b, a)$ | Order-independence of message delivery |
| **Associativity** | $m(a, m(b, c)) = m(m(a, b), c)$ | Grouping-independence of batched merges |
| **Idempotency** | $m(a, a) = a$ | Duplicate delivery is harmless |

### 2.2 Semantic Conflict Model

When two operations $o_1, o_2$ are concurrent ($o_1 \parallel o_2$, neither causally precedes the other):

1. **Non-conflicting**: $o_1$ and $o_2$ affect disjoint fields or disjoint BOs → merge is union.
2. **Conflicting on `state`**: Both modify the same BO's state → MV-Register retains both values. Resolution is deferred to LogOP adjudication (§3).
3. **Conflicting on `relations`**: OR-Set add-wins semantics apply. If $o_1$ adds to `entails` and $o_2$ removes the same entry, the add wins.

**Prohibition (P-LWW):** Conflict resolution MUST NOT use Last-Writer-Wins (LWW) based on wall-clock timestamps. Physical clocks are unreliable in distributed systems with clock skew. Causal ordering (vector clocks or dotted version vectors) is REQUIRED.

### 2.3 Causal Ordering

Each operation carries a **dot** $(i, c)$ where $i$ is the replica identifier and $c$ is a monotonically increasing counter. The causal history of a replica is the set of dots it has observed:

$$\text{ctx}(r) = \{(i, c) \mid \text{replica } r \text{ has delivered operation } (i, c)\}$$

Two operations are concurrent iff neither dot is in the other's causal context:
$$(i_1, c_1) \parallel (i_2, c_2) \iff (i_1, c_1) \notin \text{ctx}(r_2) \land (i_2, c_2) \notin \text{ctx}(r_1)$$

---

## 3. LogOP Veto Saturation Rules

### 3.1 LogOP Definition

The Logarithmic Opinion Pool aggregates $n$ agent opinions $p_1, \ldots, p_n$ with weights $w_1, \ldots, w_n$ ($\sum w_i = 1$):

$$P_{\text{LogOP}}(H|E) = \frac{1}{Z} \prod_{i=1}^{n} p_i(H|E)^{w_i}$$

where $Z$ is the normalization constant. LogOP is **externally Bayesian**: if each $p_i$ is derived from independent evidence via Bayes' rule, the aggregate is also Bayesian.

### 3.2 Saturation Bound

**Invariant (VETO-SAT):** No single agent $k$ can drive the aggregate to exact zero without audited authorization:

$$\forall k: p_k(H|E) \ge \epsilon_{\min} > 0$$

where $\epsilon_{\min}$ is the **epistemic floor** (system parameter, default $10^{-6}$). If agent $k$ submits $p_k = 0$:

1. The value is clamped to $\epsilon_{\min}$.
2. A `VETO_ATTEMPTED` event is emitted to the audit log.
3. Collapse to effective zero ($P < \epsilon_{\text{collapse}}$) requires:
   - **Path A**: L3 Supervisor explicitly authorizes via signed attestation, OR
   - **Path B**: Reinforced quorum ($\ge \lceil 2n/3 \rceil + 1$ replicas) independently confirm $p_k < \epsilon_{\min}$.

### 3.3 Interaction with `consensus_weight`

Each agent's `consensus_weight` $w_i$ is a function of historical epistemic accuracy:

$$w_i = \frac{\text{accuracy}_i^\alpha}{\sum_j \text{accuracy}_j^\alpha}$$

where $\alpha$ controls concentration (higher $\alpha$ = more weight to accurate agents). Weights are recalculated periodically (not at every operation) to prevent gaming.

### 3.4 ZK Proof Integration (EXPERIMENTAL)

When a veto survives L3 audit, a Zero-Knowledge proof SHOULD be generated attesting:
- The veto was cast by an authorized agent (identity binding)
- The evidence chain is valid (provenance)
- The LogOP calculation is correct (arithmetic circuit)

Without revealing the specific evidence content. **Formal ZK circuit specification: PENDING.**

---

## 4. Tombstones & Garbage Collection

### 4.1 Tombstone Semantics

When a BeliefObject transitions to DISCARDED, it MUST NOT be physically deleted. Instead:

1. A **tombstone marker** is created: `{belief_id, discarded_at, discarded_by, cause_ref}`.
2. The tombstone is replicated via the same CRDT channel as active beliefs.
3. Concurrent operations referencing the tombstoned BO are resolved by the OR-Set add-wins rule:
   - If an operation adds to `entails` referencing a tombstoned BO, the reference is accepted but the BO remains DISCARDED (the referencing BO transitions to ORPHANED via §8 of the RFC).

### 4.2 Causal Stability Condition for GC

A tombstone may be garbage-collected only when it is **causally stable** — every replica has observed it:

$$\text{gc\_eligible}(t) \iff \forall r \in R: t.\text{dot} \in \text{ctx}(r)$$

In practice, this is approximated by a **stability frontier**: the minimum dot observed across all known replicas. Tombstones below the stability frontier are eligible for compaction.

### 4.3 GC Protocol

1. Each replica periodically broadcasts its observed context summary (compact version vector).
2. The coordinator (any replica, leader-free) computes the stability frontier.
3. Tombstones below the frontier are compacted into a `CompactionManifest` (signed, SMT-committed).
4. Physical deletion occurs only after the manifest is durably replicated.

---

## 5. Partition Reconciliation

### 5.1 Divergence During Partition

During a network partition, each partition operates independently. The CRDT lattice guarantees that:
- Local operations continue without coordination (availability).
- Each partition's state remains internally consistent.
- No data is lost — only potentially duplicated or concurrently modified.

### 5.2 Anti-Entropy Protocol

Upon partition heal:

1. **State Exchange**: Replicas exchange compact state digests (Merkle tree roots of their CRDT state).
2. **Delta Detection**: Differences are identified by comparing Merkle paths.
3. **Delta Merge**: Missing operations are exchanged and merged using the lattice join ($\sqcup$).
4. **Conflict Resolution**: MV-Register conflicts (concurrent state modifications) are surfaced to LogOP adjudication.
5. **Post-Merge Validation**: ATMS re-validates dependency graphs across the merged state. Newly orphaned beliefs are flagged.

### 5.3 Convergence Guarantee

**Theorem (Post-Partition Convergence):** After $\delta$ rounds of anti-entropy exchange (where $\delta$ is the diameter of the communication graph), all replicas converge to identical state.

*Proof sketch:* Each exchange merges states via monotonic lattice join. After $\delta$ rounds, every operation has transitively reached every replica. By idempotency and commutativity, the final state is identical regardless of exchange order. $\square$

---

## 6. Monotonicity Invariants (Summary)

| Invariant ID | Statement | Applies To |
| ------------ | --------- | ---------- |
| **MI-1** | State only grows in the lattice | All CRDT types |
| **MI-2** | Provenance entries are append-only | ProvenanceEnvelope (G-Set) |
| **MI-3** | BeliefPatches are append-only | BeliefPatch log (G-Set) |
| **MI-4** | Tombstones are monotonically accumulated until GC | OR-Set remove markers |
| **MI-5** | Causal context (version vector) is monotonically increasing | All replicas |
| **MI-6** | `consensus_weight` adjustments are logged immutably | LogOP weight recalculation |

---

## References

- Shapiro, M., Preguiça, N., Baquero, C., Zawirski, M. (2011). *Conflict-free Replicated Data Types.* SSS 2011.
- Shapiro, M., Preguiça, N., Baquero, C., Zawirski, M. (2011). *A comprehensive study of Convergent and Commutative Replicated Data Types.* INRIA RR-7506.
- Bieniusa, A., et al. (2012). *An Optimized Conflict-free Replicated Set.* arXiv:1210.3368.
- Genest, B., Podelski, A. (2007). *On the Logarithmic Opinion Pool.* UAI 2007.
