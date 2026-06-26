# BABYLON-60 Formal Semantics (Phase 0: Runtime Bootstrap)

## 1. Syntax and Type System

### 1.1. Type Domain
The domain of types $\mathbb{T}$ is strictly defined as:
$\tau \in \{I64, TIME, F60, UNALLOCATED\}$

Values $v$ are pairs of type and data: $v : \tau \times \mathbb{D}_\tau$, where:
- $\mathbb{D}_{I64} = \mathbb{Z}$
- $\mathbb{D}_{TIME} = \mathbb{N}$ (nanoseconds or ticks)
- $\mathbb{D}_{F60} = \mathbb{Z} \times \mathbb{N}$ (represented as exact rationals $num / 60^{scale}$)

### 1.2. Typing Rules (Static Validation)
`ALLOC R_x, τ` transitions the type environment $\Delta$:
$\Delta \vdash \text{ALLOC } R_x, \tau \implies \Delta[R_x \mapsto \tau]$

Type preservation is strictly enforced: `BA.EXACT` requires both operands to be $F60$ or upcastable to $F60$. Division by zero is statically checked where possible; dynamically it forces a `CRITICAL_HALT`.

## 2. Abstract Machine & Temporal Model

### 2.1. Temporal Domains
BABYLON-60 entirely decouples physical time from causal execution:
- **$C_{phys}$ (Physical Clock)**: External entropy ($\mathbb{N}$ in ns). Strictly forbidden from influencing state transitions.
- **$C_{log}$ (Logical Clock)**: Scheduler tick ($\mathbb{N}$). Advances by $+1$ for every scheduling loop iteration or executed instruction.
- **$C_{sim}$ (Simulation Epoch)**: Mathematical time ($\mathbb{N}$), advanced by explicit events.

### 2.2. State Tuple
The global state $\Gamma$ is a deterministic automaton:
$\Gamma = \langle \mathcal{R}, \mathcal{H}, \mathcal{L}, \mathcal{Q}, C_{log} \rangle$

Where:
- $\mathcal{R}$: Register file environment $\rho : Reg \to v$
- $\mathcal{H}$: Memory Heap (versioned allocations)
- $\mathcal{L}$: DAG Ledger of causal events
- $\mathcal{Q}$: Coroutine queues partitioned into $Q_{ready}$ and $Q_{suspended}$

A coroutine frame is $q = \langle id, PC, \rho \rangle$.

## 3. Small-Step Operational Semantics ($\Gamma \vdash op \to \Gamma'$)

Transitions are atomic and strictly deterministic.

### 3.1. Concurrency Model: FORK
$\frac{target \in \text{Labels}}{\Gamma, q \vdash \text{FORK}(target) \to \Gamma[Q_{ready} \leftarrow Q_{ready} \cup \{q_{new}\}], \mathcal{L} \leftarrow \mathcal{L} \cup \{E_{fork}\}}$
*Progress*: The parent coroutine advances $PC$.
*Preservation*: The new coroutine $q_{new}$ starts with a clean $\rho$ and $PC = target$.

### 3.2. Synchronization: AWAIT
$\frac{E \in \mathcal{L}}{\Gamma, q \vdash \text{AWAIT}(E) \to q[PC \leftarrow PC+1]}$ (Event already observed)

$\frac{E \notin \mathcal{L}}{\Gamma, q \vdash \text{AWAIT}(E) \to \Gamma[Q_{susp} \leftarrow Q_{susp} \cup \{q[state \leftarrow Waiting(E)]\}]}$
*Absence of Deadlocks*: The system ensures progress as long as $\exists q \in Q_{ready}$. If $Q_{ready} = \emptyset$ and $Q_{susp} \neq \emptyset$, the system is in a deterministic deadlock, mathematically representable in the Proof IR.

### 3.3. Temporal Suspension: AFTER
$\frac{\text{target\_time} = C_{log} + ticks}{\Gamma, q \vdash \text{AFTER}(ticks) \to \Gamma[Q_{susp} \leftarrow Q_{susp} \cup \{q[state \leftarrow WaitingTimer(target\_time)]\}]}$

### 3.4. Causal Effect: EXECUTE
$\frac{E_{exec} = \text{Event}(action, parents=\text{latest}(\mathcal{L}), C_{log})}{\Gamma, q \vdash \text{EXECUTE}(action) \to \Gamma[\mathcal{L} \leftarrow \mathcal{L} \cup \{E_{exec}\}], q[PC \leftarrow PC+1]}$

## 4. DAG Ledger Canonical Serialization

The Ledger $\mathcal{L}$ is a Directed Acyclic Graph. To guarantee reproducibility across heterogeneous backends, $\mathcal{L}$ must be canonically serialized.

### 4.1. Invariants
- **Acyclicity**: $\forall e \in \mathcal{L}, e \notin \text{ancestors}(e)$
- **Topological Order**: Events are emitted sequentially; causal parents strictly precede descendants.

### 4.2. Canonical Serialization Rule
$\text{Canonical}(\mathcal{L}) = \text{Sort}_{lexicographic}(\text{TopologicalSort}(\mathcal{L}))$
For any two events $E_a, E_b$ with no causal path between them, their ordering is resolved via lexicographical comparison of their canonical string representation.

## 5. Proof IR Translation

The `Proof IR` translates $\Gamma \to \Gamma'$ transitions into explicit theorem prover obligations:
- Every instruction maps to a state transformation $\Sigma: \Gamma_i \to \Gamma_{i+1}$.
- `BA.EXACT` maps to $\Sigma$ alongside the obligation $\Pi: divisor \neq 0$.

Requirements for Lean 4/Coq backends:
1. They must implement a model of $\Gamma$.
2. They must parse the `proof.ir` S-expressions.
3. They must auto-generate proofs that $\Sigma_i$ satisfies all $\Pi_i$.

## 6. The Theorem of BABYLON

The core theorem proving the semantic correctness of the engine:

**Theorem (Operational-Semantic Isomorphism):**
$\forall P \in \mathbb{AST}, \text{Canonical}(\mathcal{L}_{Runtime(P)}) \equiv \text{ProofIR}(P).L$

**Auxiliary Lemmas:**
1. *Determinism*: $\Gamma \vdash op \to \Gamma'$ and $\Gamma \vdash op \to \Gamma'' \implies \Gamma' = \Gamma''$.
2. *Causal Conservation*: No event $E$ can exist in $\mathcal{L}$ without a continuous trace of mathematical preconditions resolving to $PC=0$.
3. *Physical Independence*: $\forall C_{phys}, C'_{phys}, Runtime(P, C_{phys}) \equiv Runtime(P, C'_{phys})$.

Proof of these properties requires no external hypotheses other than the assumption of a POSIX-compliant underlying file system for trace extraction.
