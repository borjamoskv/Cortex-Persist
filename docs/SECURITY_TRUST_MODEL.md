<!-- [C5-REAL] Exergy-Maximized -->
# SECURITY_TRUST_MODEL.md — CORTEX Persist

Package: cortex-persist v1.0.0
License: Apache-2.0 · Python: >=3.10 · Execution: C5-REAL

This document describes trust boundaries, verification surfaces, and cognitive/state-mutation risks
for the CORTEX-Persist sovereign persistence substrate.

For vulnerability disclosure policy and repository security reporting, see
[`SECURITY.md`](https://github.com/borjamoskv/Cortex-Persist/blob/main/SECURITY.md).

## Purpose: The Doctrinal Formula

> **CORTEX-Persist no confía en outputs.**
> La probabilidad puede sugerir. Solo la verificación puede gobernar.

This document defines the trust boundaries, guarantees, non-guarantees, and verification surfaces of CORTEX Persist.

The fundamental problem of modern AI agents is not that they hallucinate; it is that their probabilistic output is granted ontological status before being verified. **We do not build systems that trust the model. We build systems where unverified probabilistic output cannot survive long enough to matter.** CORTEX treats all generative output as *thermodynamically unstable conjecture* (`Void-State`).

CORTEX is not secure because it stores data. CORTEX is secure to the extent that it constrains who may mutate state, under which conditions, forcing probabilistic suggestions to cross a deterministic admission pipeline—formal schema validation, cryptographic ledger inscription, Ed25519 sovereign sealing, and causal taint tracking—before becoming actionable memory.

## Security Posture

CORTEX assumes that non-trivial inputs may be malformed, deceptive, stale,
contradictory, or adversarial.

This includes:

- human input
- agent input (including swarm-originated AEON-0 AST mutations)
- upstream model output
- tool return values
- external API responses
- replayed or duplicated facts
- semantically valid but operationally dangerous content
- EXA-LISP programs submitted for L0 execution

Generative outputs are treated as proposals, not trusted state.

## Trust Boundary

The core trust boundary is the write path.

A proposal may only become durable state after crossing deterministic controls:

```text
proposal
  → guards (14+ sovereign guards: contradiction, dependency, exergy, ZK, capability, frontier, ...)
  → schema/type validation (Pydantic v2)
  → policy/admission checks (TelemetryGate)
  → Ed25519 sovereign seal verification
  → Z3 thermodynamic bound verification (AEON-0)
  → encryption (AES-256-GCM via cortex/crypto/)
  → ledger/audit recording (SHA-256 hash-chain + AOF binary + ZK-Seal)
  → ZeroCopyRingBuffer O(1) dispatch (mmap, lock-free)
  → persistence (modular cortex-core/persistence/ subpackage)
```

If any required control fails, the write aborts.

---

## Architectural Overview (LEGION-10k Design Target)

The persistence and trust layer is organized into sovereign domains under the root `cortex/` package:

| Domain | Responsibility |
|---|---|
| `cortex/engine/` | Core CRUD, Kinetic Engines (EntropyAnnihilator, AutoCrystallizer), fact store, causal scheduler |
| `cortex/audit/` | Master Ledger — immutable hash-chain for all actions (`ledger.py`) |
| `cortex/memory/` | Large public API surface for fact persistence and retrieval |
| `cortex/guards/` | Admission, contradiction, dependency, and sovereign seal verification |

**Execution & Delivery (`cortex/delivery/` & `cortex/swarm/`):**
- `outbox.py` — Lock-free task dispatch integration.
- `ZeroCopyRingBuffer` — O(1) lock-free execution (Rust-FFI integration).

**Trust & Crypto (`cortex/crypto/`):**
- AES-256-GCM encryption at rest.
- Ed25519 Sovereign key vault management.

---

## Security Goals

CORTEX aims to provide:

- durable auditability of write behavior via dual-layer ledger (SQLite + AOF binary)
- cryptographic continuity across facts via SHA-256 hash-chain
- Ed25519 sovereign sealing (ZK-Seal) for tamper-evidence
- encrypted storage of sensitive fact content and metadata (AES-256-GCM)
- tenant-aware data isolation
- deterministic rejection of structurally invalid inputs
- explicit validation boundaries between stochastic proposals and durable state
- inspectable failure rather than silent permissiveness
- thermodynamic (exergy) bounding of all computational operations
- lock-free O(1) execution guarantees on the hot path

---

## Guarantees

CORTEX is designed to guarantee, within correct implementation and deployment:

### 1. Cryptographic Traceability

Persisted facts participate in a dual-layer ledger continuity model:
- **SQLite**: `ledger_records` table with hash-chained entries
- **AOF Binary**: C-contiguous append-only file (`cortex_ledger_aof.bin`) with struct-packed records
- **Hash Chain**: `SHA-256(previous_hash + action + vector_id + yield + timestamp)`

### 2. Sovereign Ed25519 Sealing

Every ledger entry is signed with a persistent Ed25519 keypair (`cortex_sovereign.pem`).
The `verify_zk_seal()` method allows independent verification of any sealed record.

### 3. Encrypted At-Rest Storage

Sensitive content and metadata are encrypted before persistence via `cortex/crypto/`:
- `aes.py` — AES-256-GCM encryption/decryption
- `keyring.py` — OS-level keyring integration
- `vault.py` — Sovereign key vault
- `shredder.py` — Cryptographic data destruction

### 4. Auditable Write Path

State mutation emits audit-relevant trace data through:
- Ledger hash-chain entries
- AOF binary records (single-syscall batch writes)
- Exergy Sentinel telemetry
- Execution ledger (`cortex_execution_ledger` table)

### 5. Deterministic Structural Rejection

Inputs that fail required syntax, type, schema, or guard conditions are rejected.
The guard layer includes 14+ specialized guards:

| Guard | Function |
|---|---|
| `contradiction_guard.py` | Detects conflicting state insertions |
| `dependency_guard.py` | Validates upstream dependencies |
| `exergy_guard.py` | Enforces thermodynamic exergy bounds |
| `zk_guard.py` | Verifies ZK-Seal authenticity |
| `capability_guard.py` | Capability-based access control |
| `frontier_guard.py` | Frontier exploration bounds |
| `health_guard.py` | System health preconditions |
| `path_guard.py` | Protected filesystem path enforcement |
| `url_guard.py` | URL validation and sanitization |
| `scrape_guard.py` | Web scraping safety checks |
| `thermodynamic.py` | Exergy/entropy balance enforcement |
| `sovereign_seals.py` | Sovereign seal verification pipeline |
| `heuristic_seals.py` | Heuristic-based seal generation |
| `virgo.py` | Formal verification integration |

### 6. Tenant-Aware Isolation

Data operations preserve tenant boundary semantics.

### 7. Failure Locality

Invalid proposals fail before contaminating downstream durable state.
The `ZeroCopyRingBuffer` enforces C5-REAL isolation: tasks that exceed buffer capacity
are dropped with explicit `RuntimeError` rather than silent degradation.

### 8. Lock-Free O(1) Hot Path (Zero-GIL)

The `ZeroCopyRingBuffer` relies on `cortex_rs` Rust-FFI memory mapping, completely bypassing the Python GIL. It uses `mmap`-backed C-contiguous memory with lock-free atomic reservations. There is NO `threading.Lock()` on the write or read hot path, enabling 100k+ agents/sec deterministic throughput.

---

## Non-Guarantees

CORTEX does not guarantee:

- semantic truth
- correctness of external models
- safety of upstream tools or providers
- correctness of external APIs
- absence of malicious intent in upstream sources
- correctness of business logic added outside trust boundaries
- safety if callers bypass guards, policy, or verification surfaces
- magical immunity from bad architecture layered above it
- on-chain settlement (DarkPoolZK yield negotiation is C4-SIM without deployed L2 contracts)
- hardware provisioning success (HardwareAggressor Akash deployment depends on external CLI)

A cryptographically logged lie is still a lie. It is merely an auditable lie.

---

## Trust-Surface Threat Model

Representative threats include:

### Prompt / Instruction Injection

Inputs attempt to coerce the system into bypassing intended policy or semantics.

### Contradictory State Insertion

Inputs attempt to create durable memory that conflicts with validated prior state.
**Mitigation**: `contradiction_guard.py` performs semantic conflict detection.

### Dependency Contamination

Proposal depends on false, stale, or unverifiable upstream assumptions.
**Mitigation**: `dependency_guard.py` validates causal chains.

### Silent Schema Drift

A change in structure weakens invariants without obvious runtime failure.

### Ledger Integrity Break

Hash continuity becomes invalid through bug, corruption, or unreviewed mutation.
**Mitigation**: Dual-layer verification (SQLite + AOF), Ed25519 seal per entry.

### Replay / Duplication

Previously accepted facts are reintroduced in a way that degrades retrieval or
alters interpretation.

### Cross-Tenant Leakage

Data path accidentally leaks or merges tenant state.

### Async Safety Failure

Blocking or cancellation bugs produce state inconsistency or partial operations.
**Mitigation**: Queue-based single-writer pattern in `LedgerManager._signer_loop()`.

### Unbounded AST Mutation

AEON-0 compiler receives mutation payloads that could expand indefinitely.
**Mitigation**: Z3 thermodynamic validation (`Z3ThermodynamicValidator.verify()`) enforces
a hard exergy bound of 1 Joule per mutation. DarkPoolZK anchor validation in
`K0Metabolism` enforces `1000 bytes per unit of exergy` bound.

### Exergy Exhaustion (EXA-LISP)

EXA-LISP programs consume unbounded computation.
**Mitigation**: `ExergyEnvironment` with explicit Joule limits. `EntropyDeath` exception
halts execution when budget is exceeded. Negative yield is recorded in the ledger.

### Time-Jacking Attack

Monotonic clock manipulation to break ledger ordering.
**Mitigation**: `LedgerManager.append()` detects non-monotonic timestamps and
increments by 0.001s minimum, logging a `SECURITY ALERT`.

### Ring Buffer Overflow

Task injection rate exceeds buffer capacity.
**Mitigation**: `ZeroCopyRingBuffer.enqueue()` returns `False` on full buffer.
`enqueue_swarm_task()` raises explicit `RuntimeError` — tasks are dropped to
preserve C5-REAL thermodynamic bounds rather than silently queued.

---

## Defense in Depth

CORTEX relies on layered control, not a single magic wall.

### Guards Layer

14+ specialized guards operate before persistence:

- **Contradiction Guard** — semantic conflict detection
- **Dependency Guard** — causal chain validation
- **Exergy Guard** — thermodynamic resource bounding
- **ZK Guard** — cryptographic seal verification
- **Capability Guard** — capability-based access control
- **Frontier Guard** — exploration scope bounding
- **Path Guard** — protected filesystem enforcement
- **URL Guard** — URL sanitization and validation
- **Scrape Guard** — web scraping safety
- **Health Guard** — system health preconditions
- **Sovereign Seals** — sovereign signature pipeline
- **Heuristic Seals** — heuristic-based seal generation
- **Virgo** — formal verification integration
- **Thermodynamic** — exergy/entropy balance enforcement

### Policy / Gate Layer

- `TelemetryGate` — admission control for L1 external patches
- `AEON0Compiler.mutate()` — requires valid ZK-Seal signature before AST mutation
- `OutboxDaemon` — C5-REAL sovereign isolation rejects all unrecognized task types

### Crypto Layer

`cortex/crypto/` provides:
- AES-256-GCM encryption at rest
- OS keyring integration
- Sovereign key vault management
- Cryptographic data shredding

### Ledger Layer

Dual-layer tamper-evidence:
- **SQLite**: Hash-chained `ledger_records` with indexed access
- **AOF Binary**: Struct-packed append-only file with single-syscall batch writes
- **Ed25519 Seal**: Every entry signed with sovereign keypair

### Audit Layer

Multiple audit surfaces:
- `ledger_records` table — primary audit trail
- `cortex_execution_ledger` table — execution timing and returncode tracking
- `ExergySentinel` — continuous health monitoring with HTTP dashboard
- AOF binary file — forensic reconstruction source

### Verification Layer

- Z3 thermodynamic validation for AST mutations
- Ed25519 seal verification (`verify_zk_seal()`)
- DarkPoolZK anchor validation for swarm mutations
- Formal verification integration via `cortex/guards/virgo.py`

---

## Verification Membrane

The verification membrane is the boundary between generative uncertainty and
durable system state.

```text
LLM / tool / swarm proposal
  → guard validation (14+ sovereign guards)
  → schema / type checks (Pydantic v2)
  → policy gate (TelemetryGate / AEON-0 ZK-Seal)
  → Z3 thermodynamic bound verification
  → Ed25519 sovereign sealing
  → external verification where required
  → cryptographic logging (SHA-256 chain + AOF + ZK-Seal)
  → ZeroCopyRingBuffer O(1) dispatch
  → persistence (modular subpackage)
```

The membrane exists to convert unconstrained suggestion into constrained mutation.

---

## Ledger Integrity

### Canonical Ledger

`cortex/ledger/` (`SovereignLedger`) is the canonical trust surface for the `cortex` package.
It contains:
- `ledger_core.py` — core ledger logic
- `origin.py` — provenance tracking
- `public_export.py` — public ledger export
- `public_verifier.py` / `public_verifier_utils.py` — independent verification
- `verifier.py` — internal verification
- `writer.py` — canonical writer
- `replay.py` — replay and reconstruction
- `store.py` — persistent storage
- `queue.py` — ledger queue management
- `models.py` — ledger data models

### Sovereign Ledger (cortex-core)

`cortex-core/persistence/ledger.py` (`LedgerManager`) implements the C5-REAL
persistence-layer ledger for the swarm substrate. It provides:
- SHA-256 hash-chain continuity
- Ed25519 ZK-Seal per entry
- AOF binary append-only file
- Queue-based single-writer pattern (no locks on hot path)
- Time-jacking detection
- Bankruptcy detection and reconciliation

### Required Properties

- append-like continuity semantics
- deterministic hash derivation behavior
- stable verification path
- test coverage for continuity assumptions
- explicit review for any change affecting link formation or verification
- Ed25519 seal verification for any claimed signed entry

### Current Implementation Contract

| Layer | Algorithm | Purpose |
|---|---|---|
| Hash Chain | SHA-256 | Ledger record continuity |
| Sovereign Seal | Ed25519 | Per-entry tamper-evidence |
| AOF Binary | struct.pack (C-contiguous) | Forensic reconstruction |
| Heuristic Seals | SHA3-256 | Guard-level seal validation |

### Practical Rule

If a change can break historical verifiability, it is not a normal refactor.
It is a trust event.

---

## Encryption Model

Fact content and meta are encrypted at rest via `cortex/crypto/`.

### Operational Meaning

- sensitive payloads must not be stored plaintext
- decryption occurs on authorized read path
- key handling via OS keyring (`cortex/crypto/keyring.py`) or sovereign vault
- secrets must not be reintroduced unencrypted into secondary stores
- cryptographic shredding (`cortex/crypto/shredder.py`) for data destruction

### Practical Rule (Encryption)

"Encrypted primary store + plaintext side channel" is not security. It is cosplay.

---

## Sovereign Swarm Security

### ZeroCopyRingBuffer

The `ZeroCopyRingBuffer` is the L4 sovereign task dispatch mechanism:

- **Memory**: `mmap`-backed C-contiguous binary (`swarm_ring_vsa.bin`)
- **Capacity**: 10,000 tasks × 256 bytes = 2.56 MB
- **Layout per task**: `[Status:1][Timestamp:8][AgentIDHash:64][Payload:183]`
- **Lock-free writes**: `itertools.count()` atomic counter for slot reservation
- **Rust acceleration**: Optional `cortex_rs.ZeroCopyRingBuffer` when compiled
- **Overflow policy**: Explicit failure, not silent degradation

### OutboxDaemon

The OutboxDaemon enforces **C5-REAL Sovereign Isolation**:
- Only recognized L0 interceptors execute (`EXA_LISP`, `QUANTUM_BRANCHING`, `AST_MUTATION`, `L1_EXTERNAL_PATCH`)
- All other task types are silently rejected — no external network dispatch
- Event-driven drain loop with zero arbitrary waits

### UltraMap Topology

The `UltramapSubstrate` provides O(1) spatial-temporal tracking:
- `mmap`-backed binary (`ultramap.bin`, 96 bytes/node)
- Exergy distance calculation using SHA-256 deterministic spatial mapping
- Direct integration with ZeroCopyRingBuffer for swarm position updates

---

## Tenant Isolation

All new data operations should be tenant-aware by default.

### Risks

- implicit defaulting in unsafe contexts
- missing filters in read/search paths
- merged indexing or caching across tenant surfaces
- admin tooling that assumes single-tenant world state

### Expectation

Isolation must be explicit in APIs, search, caching, and persistence behavior.

---

## Audit Trails

The audit system exists for:

- forensic reconstruction (AOF binary + SQLite ledger)
- compliance evidence (EU AI Act traceability)
- mutation traceability (Ed25519 seals)
- incident investigation (ExergySentinel telemetry)
- operational trust (execution ledger timing data)

Auditability is not a substitute for correctness.
It is the condition that makes correctness failures inspectable.

---

## Compliance Posture

CORTEX positions audit trails, decision traceability, and deterministic validation
as foundations for regulated AI environments, including EU AI Act-adjacent needs.

This should be stated carefully.

**Correct Claim:**
"The system is designed to support traceability, auditability, and constrained
state mutation via SHA-256 hash-chains, Ed25519 sovereign seals, and append-only
binary ledger files."

**Weak Claim:**
"The system is compliant because we said 'compliance' near some hashes."

Compliance is not a vibe. It is evidence.

> For vulnerability disclosure and reporting, see [`SECURITY.md`](https://github.com/borjamoskv/Cortex-Persist/blob/main/SECURITY.md).

---

## Failure Domains

Critical failure domains include:

- write-path validation
- ledger integrity (both SQLite and AOF binary layers)
- Ed25519 key management (loss of `cortex_sovereign.pem` breaks seal verification)
- migrations
- tenant isolation
- async transactional correctness (single-writer queue pattern)
- policy bypass (TelemetryGate, AEON-0 ZK-Seal checks)
- index consistency
- external provider misclassification or drift
- ZeroCopyRingBuffer overflow under sustained load
- mmap file corruption or truncation
- EXA-LISP exergy budget bypass
- AEON-0 Z3 validator circumvention

These domains deserve explicit review before release.

---

## Release Review Checklist for Trust Surfaces

Before release, review:

- [ ] guard behavior changes (14+ guards in `cortex/guards/`)
- [ ] ledger continuity changes (SHA-256 chain, AOF format, Ed25519 seal)
- [ ] encryption path changes (`cortex/crypto/`)
- [ ] policy/gate changes (TelemetryGate, AEON-0 admission)
- [ ] migration safety
- [ ] tenant isolation behavior
- [ ] async cancellation/timeout behavior (single-writer signer loop)
- [ ] audit event completeness
- [ ] API surfaces that can mutate state
- [ ] ZeroCopyRingBuffer memory layout changes
- [ ] UltraMap topology binary format changes
- [ ] EXA-LISP exergy bound enforcement
- [ ] AEON-0 Z3 thermodynamic validator bounds
- [ ] sovereign keypair rotation or format changes
- [ ] AOF struct format changes (backward compatibility)

---

## Guiding Rule

CORTEX does not make models truthful.
It reduces their freedom to contaminate persistent state.

---

## Related Documents

- [`SECURITY.md`](https://github.com/borjamoskv/Cortex-Persist/blob/main/SECURITY.md)
- [`AGENTS.md`](https://github.com/borjamoskv/Cortex-Persist/blob/main/AGENTS.md)
- [`architecture.md`](architecture.md)
- [`AXIOMS.md`](AXIOMS.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`OPERATIONS.md`](OPERATIONS.md)
- [`CORTEX_ARCHITECTURE_WHITEPAPER.md`](CORTEX_ARCHITECTURE_WHITEPAPER.md)
- [`thermodynamic-enforcement.md`](thermodynamic-enforcement.md)
- [`IMMUNITY-LAYER.md`](IMMUNITY-LAYER.md)
- [`RFC_02_CORTEX_SECURITY_SPEC.md`](RFC_02_CORTEX_SECURITY_SPEC.md)
