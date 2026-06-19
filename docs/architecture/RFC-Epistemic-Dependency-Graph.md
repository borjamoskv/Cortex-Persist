# RFC: Epistemic Dependency Graph (EDG) & Invalidation Propagation

> **Author**: MOSKV-1
> **Status**: Accepted (Core Theoretical Shift)
> **Layer**: Protocol / Engine

## 1. The Core Pivot: From Knowledge to Epistemic Transitions

CORTEX-Persist is no longer classified simply as a "Knowledge Engine" or "Agent Memory". It is formally defined as:

**A distributed system for managing the formal lifecycle of verifiable claims.**

Knowledge is not storage. Knowledge is a **Dynamic Dependency Structure**. The fundamental unit of the system is not the `KnowledgeObject`, but the **Epistemic State Transition**.

## 2. The Epistemic Dependency Graph (EDG)

The system is modeled as a Directed Acyclic Graph (DAG) where:
- **Node**: An Epistemic Object (Claim, Evidence, Verification, Code Block).
- **Edge**: A Dependency Relation (e.g., `supports`, `verifies`, `derives_from`).

### Example Graph:
```text
[Evidence: Log Trace] ──supports──► [Claim: API is stable]
                                          │
[Verification: Test pass] ──supports──────┘
                                          │
                                   ──supports──► [Decision: Merge PR]
```

## 3. Epistemic Invalidation Propagation (Garbage Collection for Truth)

Unlike standard databases that store isolated facts, the EDG tracks causal dependencies. If an underlying epistemic object is falsified or deprecated, the invalidation must propagate mathematically through the graph.

### The Invalidation Rule:
If `Node(A) → Invalid`, then:
- `Confidence(B)` decreases for all `B` where `A ──supports──► B`.
- If `Confidence(B)` falls below `THRESHOLD_STABLE`, `B → Metastable`.

This behaves as an **Epistemic Garbage Collector**, pruning decision trees that rely on falsified evidence without requiring manual human intervention.

## 4. Formal Invariants (Epistemic Consistency)

To achieve parity with distributed systems primitives (like CRDTs for convergence or BFT for state consistency), CORTEX enforces **Epistemic Consistency**:

> **No accepted node can depend on an invalidated chain of support.**

```math
\text{Accepted}(K) \implies \forall d \in \text{Dependencies}(K), \text{Valid}(d)
```

If a foundational assumption of a codebase is broken, every architectural decision relying on that assumption is automatically flagged as `Challenged` or `Deprecated`.

## 5. Lifecycle of an Epistemic Claim

Every node in the EDG traverses a strict state machine:
1. `Hypothesized` (Proposed by LLM)
2. `Supported` (Evidence attached)
3. `Verified` (Passed deterministic guards)
4. `Accepted` (Committed to Ledger)
5. `Challenged` (Conflicting PR or failing test)
6. `Deprecated` (Replaced by better implementation)
7. `Superseded` (Archived)

## 6. Implementation Implications for the PR Risk Firewall (MVP)

How does this map to the CI/CD Firewall we are building?
- **Blast Radius = EDG Traversal**: When an AI submits a PR modifying `Function A`, CORTEX traverses the EDG to find all `Claims` that depend on `Function A`.
- If `Function A` supports `Security Policy B`, and the PR modifies it, the PR triggers a `CRITICAL` risk alert.
- The Firewall is essentially performing a runtime Epistemic Invalidation Check before allowing the merge.
