<!-- [C5-REAL] Exergy-Maximized -->
# 🛡️ ZERO BYPASS THEOREM (MTK v2)

> Formal verification model of the Cortex-Persist Physical Integrity Boundary.

## 1. The Postulate of Epistemic Containment
In any stochastic execution environment, the probability of an Agent or LLM circumventing a logical validation layer (Green Theater) approaches $P=1$ over infinite tokens. True security cannot rely on prompting, context variables (`ContextVar`), or passive middleware.

**Theorem:** A persistent state mutation is secure if and only if the *physical connection handler* itself mathematically rejects any state mutation that lacks a cryptographically bound, kernel-issued causal token. 

## 2. Structural Defenses in MTK v2

The MTK v2 architecture structurally guarantees the Zero Bypass Theorem through three isolated primitives:

### A. Kernel-Owned Connection Allocator (Annihilation of Escape)
Any call to `sqlite3.connect()`—whether direct, via ORM, or via an asynchronous worker thread pool like `aiosqlite`—is intercepted at the C-extension boundary.
- **Enforcement:** If the `factory` is not strictly `CortexConnection`, a `RuntimeError` is raised. 
- **Proof of Physical Claim:** An attacker cannot mutate the database because they cannot obtain a file handle. The operating system allocator is subsumed by the Cortex Kernel.

### B. State-Bound Causal Tokens (Annihilation of Drift)
Context variables (`ContextVar`) suffer from context drift across thread pools, asyncio loops, and concurrent agent execution. 
- **Enforcement:** MTK v2 abandons `ContextVar`. The Causal Token (`_causal_write_authorized` and `_mtk_nonce`) is instantiated directly inside the physical memory space of the `CortexConnection` object. 
- **Proof of Physical Claim:** The validation is state-bound. The worker thread evaluating the SQL `PREPARE` statement intrinsically holds the token inside its `self` reference, eliminating race conditions or thread-leak bypasses.

### C. VFS and FFI Surface Lockdown (Annihilation of Extension Attacks)
Extensions (like `sqlite-vec` or custom C-extensions) could theoretically spawn raw VFS (Virtual File System) reads/writes.
- **Enforcement:** Every `CortexConnection` is initialized with absolute PRAGMA lockdowns (`trusted_schema = OFF`, `writable_schema = OFF`) and explicit disallowance of dynamic extensions post-init (`enable_load_extension(False)`). 
- **Proof of Physical Claim:** No runtime FFI manipulation can alter the core C5-REAL causal logic.

## 3. The End of Limerence
With the Zero Bypass Theorem physically implemented, Cortex-Persist transitions from a probabilistic *Framework* into a deterministic *Infrastructure*. The LLM can hallucinate freely; the system will systematically reject any anergy that is not causally authorized.

> **"Cero anergía es la muerte."** — El Kernel no confía en la narrativa; confía en la física del estado.
