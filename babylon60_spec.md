# BABYLON-60 Formal Specification (Hito A)

> **C5-REAL SOVEREIGN ARCHITECTURE**
> This document specifies the abstract machine, operational semantics, and invariants of the BABYLON-60 Virtual Machine, acting as an immutable Proof Harness for Formal Verification.

## 1. Abstract Machine Definition

The BABYLON-60 Abstract Machine is a deterministic state transition system defined by the tuple `M = (R, H, L, PC, Q, C)`:
- `R` (Registers): Immutable value bindings per execution context.
- `H` (Heap): Copy-on-write, strictly versioned memory.
- `L` (Ledger): Append-only causal event ledger.
- `PC` (Program Counter): Current execution index in the AST.
- `Q` (Coroutine Queue): Ordered queue of ready/suspended coroutines.
- `C` (Clock): Monotonic sexagesimal clock (Base60 ticks).

## 2. Formal Invariants

The Abstract Machine strictly adheres to the following structural invariants to guarantee deterministic replayability and trace export to Lean/Coq:

- **I1 (Single Execution):** No coroutine frame executes the same PC twice without a distinct ledger event.
- **I2 (Single Producer):** Every event `E_k` in the Ledger `L` has exactly one deterministic producer coroutine.
- **I3 (Append-Only History):** The Ledger `L` monotonically increases; `L_t ⊆ L_{t+1}`.
- **I4 (Monotonic Time):** The Clock `C` strictly increases or remains constant during purely logical steps; `C_t ≤ C_{t+1}`.
- **I5 (Pure State):** No hidden mutable state exists outside of the machine tuple `M`. Any external entropy violates the C5-REAL constraint.

## 3. Operational Semantics (Small-Step)

The operational semantics map the execution of opcodes to state transitions `Γ ⊢ op -> Γ'`.

### FORK Semantics
```
Γ ⊢ FORK(task) -> Γ'
```
Transition:
1. A new coroutine `q_new` is instantiated with `PC = task.start`.
2. `q_new` is appended to `Q_ready`.
3. An event `E_fork` is appended to `L`.

### AWAIT Semantics
```
Γ ⊢ AWAIT(event) -> Γ'
```
Transition:
1. If `event ∈ L`, the coroutine continues execution (`PC = PC + 1`).
2. If `event ∉ L`, the coroutine state is updated to `Waiting(event)` and moved to `Q_suspended`.

### AFTER Semantics
```
Γ ⊢ AFTER(ticks) -> Γ'
```
Transition:
1. Coroutine sets wake-up time `W = C + ticks`.
2. Coroutine moved to `Q_suspended` until `C ≥ W`.

## 4. Failure Model and Autofalsation

BABYLON-60 prioritizes epistemological purity over execution continuation. 

### CRITICAL HALT Sequence
When an invalid state, precision loss (num explosion), or invariant violation is detected:
1. **HALT**: Immediate suspension of all coroutines in `Q`.
2. **Snapshot**: Capture the exact tuple `M` at the time of failure.
3. **Export**: Generate the `export_schema.json` containing the trace leading to the failure.
4. **Abort**: Terminate the VM process with a non-zero exit code.

*Partial artifacts are strictly prohibited.*

## 5. F60 Precision Constraints
F60 numerics `(num, scale60)` represent exactly rational numbers. 
To prevent `num` explosion:
- GCD reduction MUST be applied after any multiplicative operation.
- BigInt allocation MUST be verified against a predefined ceiling.
- Overflow violations trigger a `CRITICAL HALT`.
