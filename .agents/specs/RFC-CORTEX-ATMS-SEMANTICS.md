# Appendix: ATMS Dependency Indexing Formalism

> **Status:** EXPERIMENTAL — Open Formal Appendix v0.1
> **Parent RFC:** [RFC-CORTEX-NATIVE-AI v0.1](file:///.agents/workflows/RFC-CORTEX-NATIVE-AI.md)
> **Date:** 2026-03-14

---

## 0. Preamble

This appendix formalizes the Assumption-Based Truth Maintenance System (ATMS) semantics
for Cortex-Persist. An ATMS maintains a record of which assumptions underlie each belief,
enabling efficient dependency-directed backtracking when assumptions are invalidated.

Unlike a standard TMS which tracks a single consistent worldview, the ATMS
maintains *all possible* consistent environments simultaneously, allowing the system
to reason about multiple hypothetical states without reconstruction cost.

---

## 1. Graph Dependency Structures

### 1.1 Definitions

- **Node** $n$: A `BeliefObject` in the CORTEX ontology.
- **Assumption** $a$: A node with no justifications — accepted axiomatically.
- **Justification** $J = \langle \{a_1, \ldots, a_k\}, n \rangle$: Node $n$ is believed if all assumptions $a_1, \ldots, a_k$ hold.
- **Environment** $E = \{a_1, \ldots, a_m\}$: A consistent set of assumptions.
- **Label** $L(n)$: The set of minimal environments under which $n$ is believed.

### 1.2 Operators

| Operator | Notation | Semantics |
|:---------|:---------|:----------|
| **Entails** | $A \vdash B$ | $B$ is believed whenever all assumptions in $A$'s label hold. Implemented via `relations.entails`. |
| **Discards** | $A \dashv B$ | $A$ provides evidence that $B$ is false. Implemented via `relations.discards`. Both $A$ and $B$ cannot be simultaneously believed in any consistent environment. |

### 1.3 Depth Limits and Light Cone

To prevent unbounded dependency chains:

- **Depth limit** $d$: The maximum causal distance from assumption to derived belief. Default: $d \le 2$ for real-time operations.
- **Light Cone** $\mathcal{L}(n, d)$: The set of all nodes reachable from $n$ within depth $d$.
- Beliefs derived beyond the light cone boundary are evaluated asynchronously (deferred work).

$$\mathcal{L}(n, d) = \{m \in N : \text{dist}(n, m) \le d\}$$

Operations within $\mathcal{L}$ have latency guarantees (TARGET: sub-10ms).
Operations outside $\mathcal{L}$ are batched into consolidation jobs.

---

## 2. Propagation Mathematics

### 2.1 Label Computation

The label of a derived node $n$ with justification $J = \langle \{a_1, \ldots, a_k\}, n \rangle$ is:

$$L(n) = \bigcup_{J \in \text{Justifications}(n)} \left( \bigcap_{i=1}^{k} L(a_i) \right)$$

where each $L(a_i)$ is the label of assumption $a_i$ (for base assumptions, $L(a) = \{\{a\}\}$).

### 2.2 Nogood Management

A **nogood** $\mathcal{N}$ is an environment known to be inconsistent (contains contradictions).

$$\mathcal{N} = \{E : \exists n_1, n_2 \in \text{Believed}(E) \text{ s.t. } n_1 \dashv n_2\}$$

When a `discards` relation is asserted between two nodes, the ATMS:

1. Computes all environments containing both nodes.
2. Marks those environments as nogoods.
3. Removes them from all labels of all nodes.

### 2.3 Root Invalidation and Orphaning

When an assumption $a$ is revoked:

1. **Immediate ($O(1)$):** The assumption's index entry is marked invalid.
   All precomputed environment references containing $a$ are flagged.
2. **Deferred propagation:** Nodes whose labels reduce to $\emptyset$ (no valid
   environments remain) transition to `ORPHANED`.
3. **Structural reconciliation:** `ORPHANED` nodes are evaluated for alternative
   justifications. If none exist, they transition to `DISCARDED`.

> [!IMPORTANT]
> The $O(1)$ claim in RFC §8 applies to step (1) — the index flag.
> Steps (2) and (3) are $O(|L(n)| \cdot |\text{affected subgraph}|)$ in the worst case.
> Precomputed dependency indices amortize this cost for common patterns.

### 2.4 Dependency-Directed Backtracking

When a contradiction is detected at node $n$:

1. Compute the minimal nogood $\mathcal{N}_{\min}$ responsible.
2. Identify the most recently assumed member of $\mathcal{N}_{\min}$.
3. Retract that assumption, triggering label recomputation for all dependents.
4. If the contradiction persists, iterate with the next most recent assumption.

This avoids chronological backtracking (which is exponential) by jumping directly
to the relevant assumption.

---

## 3. Cycle Detection

### 3.1 Definition

A causal cycle exists when:

$$n_1 \vdash n_2 \vdash \cdots \vdash n_k \vdash n_1$$

or when:

$$n_1 \vdash n_2 \vdash \cdots \vdash \neg n_1$$

(a self-refuting chain).

### 3.2 Detection Mechanism

- The ATMS maintains a **dependency DAG** indexed by UUIDv7.
- On each `entails` or `discards` assertion, a cycle check is performed:
  - If the assertion would create a cycle, it is **rejected** and escalated to the
    Tribunal (LogOP adjudication with human-in-the-loop).
- Cycle detection is $O(|E|)$ where $|E|$ is the edge count in the local light cone $\mathcal{L}$.

### 3.3 Resolution

Cycles detected by the ATMS are handled by:

1. **Breaking the weakest link** — the edge with lowest `confidence_score`.
2. **Tribunal escalation** — if no edge is clearly weakest, the cycle is presented
   to the consensus protocol for resolution.
3. **Quarantine** — all nodes in the cycle are moved to `CONTESTED` until resolved.

---

## 4. Interaction with CRDT Sync

### 4.1 Cross-Replica Label Consistency

When two replicas merge their ATMS states:

- Labels are merged using set union: $L_{\text{merged}}(n) = L_{r_1}(n) \cup L_{r_2}(n)$.
- Nogoods are merged using set union: $\mathcal{N}_{\text{merged}} = \mathcal{N}_{r_1} \cup \mathcal{N}_{r_2}$.
- Post-merge cleanup: remove any environments from labels that are now nogoods.

This operation is commutative and idempotent, satisfying CRDT requirements.

### 4.2 Causal Consistency

The ATMS dependency graph inherits causal ordering from UUIDv7 timestamps.
Cross-replica merges respect this ordering: a justification cannot reference
a node with a later timestamp (causal violation → reject at ingestion).

---

## 5. Formal Properties Summary

| Property | Requirement | Status |
|:---------|:------------|:-------|
| Label minimality | SHOULD maintain minimal environments | Normative |
| Nogood completeness | MUST detect all contradictions | Normative |
| Cycle detection within light cone | MUST detect in $O(\|E\|)$ | Normative |
| Cross-replica label merge commutativity | MUST satisfy CRDT axioms | EXPERIMENTAL |
| Dependency-directed backtracking correctness | MUST avoid chronological backtracking | Normative |
| Deferred propagation bounded time | TARGET: complete within 1 consolidation cycle | EXPERIMENTAL |

---

*CORTEX-Persist · ATMS Semantics Appendix v0.1 · EXPERIMENTAL · 2026-03-14*
