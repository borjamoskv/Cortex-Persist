# RFC: Keyed Retrieval Graph System (KRGS)

> **Author**: MOSKV-1
> **Status**: Accepted (Core Theoretical Shift)
> **Layer**: Protocol / Engine

## 1. The Core Pivot: Resolving Epistemic Collapse

CORTEX-Persist was previously mislabeled under the "Epistemic Dependency Graph (EDG)" paradigm. This caused a semantic and mathematical collapse by confusing vector similarity with formal epistemic causation.

We formally enforce a separation of domains via **Keyed Retrieval Graph System (KRGS)**. 
Knowledge is a **Dynamic Dependency Structure**, but the graph and its heuristic search space live in orthogonal dimensions.

## 2. Partitioned Subspaces: Truth vs Retrieval

The architecture isolates the Invariant Logical Graph (`G`) from the Keyed Retrieval Space (`R_K`).

### 2.1 The Logical Graph (`G`)
- **Domain**: Discrete, logical, causally strict.
- **Node**: An Epistemic Claim or verified payload.
- **Edge**: A formal deterministic Causal Relation (e.g., `derives_from`, `invalidates`).
- **Invariant**: *No vector operation can modify epistemic truth.*

### 2.2 Keyed Retrieval Space (`R_K`)
- **Domain**: Continuous, euclidean, subject to quantization noise.
- **Function**: Accelerates the retrieval of epistemic nodes by similarity, bound to a specific tenant key `K`.
- **Property**: It acts as a partitioned heuristic index. Vector distances here imply semantic correlation, not causal validity.

### 2.3 Projection and Bridges
A node in `G` projects into `R_K` via an orthogonal transformation $\phi_K(x) = Q_K x + T_K$. 
A **Bridge** connects a point in `R_K` back to `G`. Bridges are strictly directional metadata pointers.

## 3. Epistemic Invalidation Propagation (Truth Garbage Collection)

If an underlying epistemic object in `G` is falsified or deprecated, the invalidation propagates strictly along the edges in `G`.
The `R_K` space is entirely passive in this process; it does not compute truth.

### The Invalidation Rule in G:
If `Node(A) → Invalid`, then:
- `Confidence(B)` decreases for all `B` where `A ──supports──► B`.
- If `Confidence(B)` falls below `THRESHOLD_STABLE`, `B → Metastable`.

## 4. Formal Invariants (Epistemic Consistency)

> **No accepted node can depend on an invalidated chain of support.**

```math
\text{Accepted}(K) \implies \forall d \in \text{Dependencies}(K), \text{Valid}(d)
```

## 5. Security by Partitioning (Threat Model)

The KRGS enforces **Security by Partitioning**. Because keys are isolated in the Vault Model and transformation $\phi_K$ applies orthogonal rotations, merging sub-spaces without the keys yields uniform noise. 

Adversarial operations like **Latent Space Inversion** or **Graph Poisoning** are neutralized at the topological level, because inserting a poisoned vector into `R_K` cannot spontaneously generate a causal edge in `G`.
