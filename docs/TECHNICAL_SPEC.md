# ⚙️ CORTEX-PERSIST: TECHNICAL SPECIFICATION (C5-REAL)

## 1. 🏗 ARCHITECTURE OVERVIEW

**CORTEX-PERSIST** acts as a CI/CD firewall for LLM-generated code. It shifts the paradigm from "trust in generation" to "trust in deterministic cryptographic lineage". 

### 1.1 The Epistemic Dependency Graph (EDG)
Generative outputs are treated strictly as **probabilistic conjectures**. These conjectures are processed through deterministic validation boundaries before mutation. The structural engine models this as an Epistemic Dependency Graph, ensuring that if a foundational node is invalidated, the blast radius is computed, and affected branches are discarded.

### 1.2 Boundary Layers: Python/Rust
- **Python (Orchestration):** Maximizes Shipping Velocity. Handles CLI routing, external hooks, and FastAPI endpoints.
- **Rust (Execution/Causal Engine):** Managed via PyO3. Bypasses the GIL, achieves microsecond lock-free latency, and manages the EDG natively.

---

## 2. 🛡 MINIMAL TRUSTED KERNEL (MTK)

CORTEX enforces atomic mutations physically at the SQLite layer, abolishing pure software "distributed sagas".

### 2.1 The Token Gate Protocol
1. **[Guard Admission]**: `mtk_core.py` verifies the closure payload and taint signature.
2. **[Token Minting]**: Mints an ephemeral cryptographic token `mtk_auth_...` using the CORTEX private key and places it in the Python `ContextVar`.
3. **[SQLite Hook]**: `mtk_authorizer_callback` intercepts ALL mutations (INSERT/UPDATE/DELETE). If the token is absent, execution is violently rejected (`SQLITE_DENY`).
4. **[Destruction]**: Token destroyed upon WAL transaction completion.

---

## 3. 📉 THERMODYNAMIC INVARIANTS (BABYLON-60)

- **Floating-Point Eradication:** All internal calculation states (metrics, timestamps, causal coordinates) use Base-60 structs. The use of `float64` is classified as a P0 Entropy Vulnerability.
- **Strict Tenant Isolation:** Cryptographic validation and memory isolation ensure cross-tenant leakage triggers immediate engine shutdown.
- **Autopoiesis Watchdog:** Active binary mutations must traverse an isolated Git Sentinel branch (`auto/moskv1-mitosis-*`) and undergo external CI pipeline compilation. The engine must never overwrite its active execution state.

---

## 4. 🗄 STATE METADATA AND TAINT ENGINE

Any artifact, code block, or text string output by a generative agent must be wrapped in `EpistemicNode` structures.
- **CORTEX-TAINT Flag:** Unverified AI outputs carry a taint. Taint metadata propagates downstream.
- **Audit Ledger:** All validations, threshold failures, and MTK token emissions are hashed (SHA-256) into `legacy_research/audit/ledger.py` utilizing `SERIALIZABLE` isolation.

`Status`: C5-REAL | `Version`: v10.0
