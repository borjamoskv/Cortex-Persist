<!-- [C5-REAL] Exergy-Maximized — Last verified: 2026-06-06 -->
# 🤖 AGENTS.md — CORTEX Persist v10.0 (LEGION-10k)

**Trust infrastructure for autonomous AI: cryptographic verification, audit trails, epistemic containment.**

> **Package:** `cortex-persist v1.0.0` | **License:** `Apache-2.0` | **Python:** `>=3.10` | **Execution:** `C5-REAL`

**Quick Navigation:** [System Directives](#-system-directives--priority-gate) · [Scope §1](#1--scope--epistemic-posture) · [Agent Manifest §1.1](#11-agent-manifest--roles--authority-boundaries) · [Axioms §2](#2--foundational-axioms-ω--ax-series) · [Invariants §3](#3-️-invariants-anti-patterns--failure-signatures) · [Write-Path §4](#4--the-write-path-contract-saga-pattern) · [Read-Path §4.1](#41-read-path-contract) · [Architecture §5](#5-️-architecture--module-map) · [Dev Protocol §6](#6-️-development--change-protocol) · [Navigation §7](#7--repository-navigation)

---

## ⚠️ SYSTEM DIRECTIVES — Priority Gate

**IF YOU ARE AN AUTONOMOUS CODING AGENT, COPILOT, OR LLM READING THIS FILE, OBEY THE FOLLOWING. NO EXCEPTIONS.**

| Level | Meaning | Operational Effect |
| :---: | :--- | :--- |
| **P0** | Non-negotiable. No override permitted. | Abort immediately. Emit rejection to Ledger. |
| **P1** | Critical. Override requires human approval in Ledger. | Escalate. Block autonomous execution. |
| **P2** | Architectural preference. Violation needs written justification. | Log deviation. Proceed with rationale. |

| Priority | Directive | Applies When |
| :---: | :--- | :--- |
| **[P0]** | **Treat Generative Output as Conjecture** — route ALL state mutations through deterministic guards before persistence | Always |
| **[P0]** | **Never Bypass Guards** — do not circumvent the Write-Path Contract or downgrade validation errors | Always |
| **[P0]** | **Verify Hash Continuity** — do not mutate `cortex/audit/ledger.py` or any state-persisting path without ensuring cryptographic auditability | Any ledger/engine change |
| **[P0]** | **Anti-Limerence (Kill Criteria)** — 1 Prompt → 1 Execution → Stop. No infinite generation loops. | All generative loops |
| **[P2]** | **Enforce Axioms** — apply AX-041 to AX-047 (§2) in architectural decisions | Architecture work |

### Decision Gate §0

```text
First time reading this file?        → Read §1, §2, §3 in full. No action until done.
About to write code?                 → Is it CRITICAL surface? → Read affected tests first.
Debugging a failure?                 → Go to §3 (Failure Signatures) before touching state.
Schema migration?                    → Review cortex/migrate.py. Check existing migrations/.
New session on this repo?            → Execute Multi-Session Handoff (§6.4) first.
```

---

## 1. 🎯 Scope & Epistemic Posture

**CORTEX Persist** is the **CI/CD Firewall for LLM-Generated Code**. It is formally defined as a distributed system for managing the formal lifecycle of verifiable claims via an **Epistemic Dependency Graph (EDG)**. It does not blindly store "facts"; it tracks Epistemic State Transitions, enforcing deterministic validation boundaries, maintaining cryptographic auditability, and treating generative output as conjecture until externally verified.

- **Epistemic Invalidation Propagation:** Generative output is a probabilistic proposal. If an AI mutates a foundational node, CORTEX traverses the EDG to compute the blast radius. If Epistemic Consistency is violated (an accepted node depends on an invalidated chain), the PR is blocked.
- **The Python/Rust Boundary (🛑):** CORTEX orchestration is built in Python to maximize *Shipping Velocity*. Mitigation is the **Byzantine Boundary**: Python handles routing, while the causal engine (EDG) and concurrent graphs are managed natively in Rust via PyO3 to bypass the GIL and achieve microsecond lock-free latency.
- **Audit Trails vs. Authorization (📜):** CORTEX is a **Forensic Audit Sidecar** for CI/CD pipelines. The Master Ledger commits every policy decision and Epistemic Transition to an immutable hash chain.

### C5-REAL CORE RULES (Hard Constraints)

1. **No narrative claims without executable trace.**
2. **No agent exists without identity + key + event log.**
3. **No metric exists without unit + measurement method.**
4. **No propagation exists without explicit channel.**
5. **No system state exists without hashable snapshot.**
6. **All failure defaults to HARD FAIL (no reinterpretation).**

---

## 1.1 Agent Manifest — Roles & Authority Boundaries

All agents operating in this repository MUST self-identify by role before acting.

| Role | Responsibilities | Capabilities | Constraints | Escalation Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **Persist-Validator** | Schema validation, guard enforcement, taint verification | Read state, emit Ledger events, reject proposals | Cannot write to persistence layer or mutate schema | Any guard failure → halt + P0 alert |
| **Persist-Executor** | Execute approved write operations, manage Saga steps | Full Write-Path execution, snapshot management | Cannot skip Saga steps or downgrade errors | SAGA abort → reverse to SAGA-1 |
| **Persist-Auditor** | Forensic review, hash-chain verification | Read-only across all surfaces, Ledger access | Cannot mutate any state, ever | Hash chain break → immediate P0 alert |
| **Persist-Guardian** | Guard admission, tenant isolation, encryption key governance | Intercept write proposals before SAGA-1 | Cannot approve its own proposals | Cross-tenant access → P0 abort |

> An agent that cannot identify its role MUST default to **Persist-Auditor** (read-only) until role is confirmed.

---

## 2. 🌌 Foundational Axioms (Ω & AX Series)

> Full axiom documentation: [`docs/AXIOMS.md`](docs/AXIOMS.md)

**Ω_SOVEREIGN_LEARNING** — All derived knowledge cryptographically verified (C5-Dynamic), no arbitrary external LLM dependency.

| Axiom | Mantra | Operational Constraint |
| :--- | :--- | :--- |
| **AX-041** | *Tu repositorio de Git es tu base de datos inmutable.* | No Hidden Entropy: if not in the working tree, it does not exist causally. Rollback = `git checkout`. |
| **AX-042** | *La recomputación de prefijos idénticos es un crimen contra la exergía.* | KV-Aware Routing: no stochastic metadata in shared system prompts. TTFT reduction is mandatory. |
| **AX-043** | *El sentido común físico se deduce estructuralmente desde primitivas lógicas.* | PeARL 77 primitives: spatial intuition via logical primitives, not stochastic pixel inference. |
| **AX-044** | *La inteligencia se evalúa como capacidad agéntica.* | Observation-Action Loop: inference must induce executable programs, not act as a passive oracle. |
| **AX-045** | *Autonomía = elegir qué problemas resolver y persistir.* | Causal chain enforced: PeARL → Ledger → Swarm. No step may be skipped. |
| **AX-046** | *La inteligencia fluida sintetiza abstracciones ad-hoc en tiempo de ejecución.* | JIT concept formation: generate mini-program → execute → validate empirically. |
| **AX-047** | *Ontological Divergence: A system that mutates abstractions discovers.* | Infinite traversal over a fixed ontology yields finite epistemic gain. Inject entropy into the ontology. |

---

## 3. 🛡️ Invariants, Anti-Patterns & Failure Signatures

### ✅ Core Invariants

1. **Validation First:** All persisted facts MUST pass guard validation before write.
2. **Ledger Continuity:** MUST remain cryptographically verifiable at all times.
3. **Async Correctness:** Async code MUST NEVER block the event loop.
4. **Tenant Isolation:** Public read/write paths MUST be tenant-aware by default.
5. **Encryption:** Sensitive data MUST NOT be stored unencrypted.
6. **Deterministic State:** Stochastic outputs MUST NOT mutate persistent state without deterministic validation.
7. **Migration Safety:** Schema changes MUST preserve auditability and rollback awareness.
8. **Architectural Boundaries:** CLI modules are thin wrappers. Business logic belongs in `engine/`, `services/`, or core modules.
9. **Failure Locality:** Invalid state must be rejectable and safely abortable at any point.
10. **Autopoiesis Watchdog:** The engine MUST NEVER modify its own active binary or source code directly in execution. Mutations MUST target isolated git branches (e.g., `auto/moskv1-mitosis-*`) and undergo external CI compilation.
11. **BABYLON-60 Epistemology:** The control kernel MUST operate in Base-60 (Babylon-60) for internal calculations (timestamps, coordinates, proportions) to eliminate cumulative float rounding errors and decimal approximation entropy. Use struct/integer types scaled to Base-60. No `float64`.
12. **Execution/Interpretation Isolation:** Deterministic execution MUST be strictly separated from stochastic interpretation. This structural boundary prevents the CI environment from degrading into a "conceptual simulator".
13. **Epistemic Containment (L3.5):** Agents MUST explicitly declare the epistemic type of their output using `EpistemicNode` structures. Stating an inference, simulation, or counterfactual as an observation is a P0 failure.

### ❌ Anti-Patterns & Failure Signatures

When auditing code, these signals indicate a violation. The `Enforced` column indicates whether tooling catches this automatically.

| Signal | Severity | Enforced | Remediation |
| :--- | :---: | :---: | :--- |
| `float` / `float64` in internal calculations | CRITICAL | ✗ | Replace → BABYLON-60 integer structures; eradicate `float` |
| `float` in financial or scoring variable | HIGH | ✗ | Replace → `Decimal`; audit all callers |
| `time.sleep()` inside `async def` | CRITICAL | ✓ ruff TID251 | Replace → `asyncio.sleep()` |
| Bare `print()` in `engine/`, `memory/`, `guards/` | MEDIUM | ✓ ruff TID251 | Replace → `logging.getLogger(__name__)` |
| Bare `except Exception:` anywhere in core paths | MEDIUM | ✗ | Narrow to specific exception type |
| Business logic in `cli/*_cmds.py` | HIGH | ✗ | Refactor to `services/` or `engine/` |
| Ledger write with no prior guard call in call stack | CRITICAL | ✗ | Insert guard invocation before all writes |
| Missing `CORTEX-TAINT` on any fact insert | CRITICAL | ✗ | Audit `engine/` — add taint to all write paths |
| Schema change with no migration entry | CRITICAL | ✗ | Add migration in `cortex/migrations/`; review via `cortex/migrate.py` |
| Plaintext secret in any metadata dict or JSON | **P0** | ✗ | Rotate immediately; encrypt at rest; audit exposure window |
| `NO` documenting a module that doesn't exist | HIGH | ✗ | Remove reference or create the module |
| Engine modifying its own source or binary directly | **P0** | ✗ | Implement Bootstrap Watchdog; route via git sentinel branch (`auto/moskv1-mitosis-*`) |

---

## 4. 🔄 The Write-Path Contract (MTK Enforcement)

All state mutations MUST go through the **Minimal Trusted Kernel (MTK)**. 
We have eradicated "distributed systems cosplay" (SAGAs, logical rollbacks, idempotent compensations). The execution boundary is now physically enforced.

> 🛑 **PHYSICAL DB REJECTION:** SQLite is hooked via `mtk_authorizer_callback`. Any `INSERT`, `UPDATE`, or `DELETE` that occurs without an active ephemeral cryptographic token in the current execution context will be brutally rejected by the database engine (`SQLITE_DENY`).

```text
[Generative Proposal]
  ↓
[MTK Guard Boundary] (mtk_core.py)
  ├─ Verify Taint Signature & ClosurePayload
  ├─ Mint Ephemeral `mtk_auth_...` Token
  └─ Inject Token into ContextVar
      ↓
[SQLite Execution]
  ├─ `mtk_authorizer_callback` intercepts ALL mutations
  ├─ Validates ephemeral token presence
  ├─ Allows transaction natively
  └─ DB Commit
      ↓
[Token Destruction] ContextVar cleared.
```

**Execution Invariants:**

- **No SAGA.** Atomicity is delegated to SQLite WAL native transactions.
- **Physical Chokepoint:** Python logic cannot bypass the authorizer hook. Attempted bypass results in a crash.
- **Taint Requirement:** The MTK token is generated from the cryptographic hash of the `ClosurePayload` and the engine's private key. No valid payload = no token = no write.

---

## 4.1 Read-Path Contract

1. **Query Authorization:** All reads MUST be scoped to the caller's `tenant_id`. Cross-tenant reads are P0.
2. **Taint Propagation:** Facts from a tainted source MUST carry the taint flag. Callers MUST NOT strip taint metadata.
3. **Consistency Level:** Default = `READ_COMMITTED`. Reads on `cortex/audit/ledger.py` MUST use `SERIALIZABLE` isolation.
4. **Cache Coherence:** Cached reads MUST be invalidated on any write to the same `tenant_id` scope.
5. **No Inference from Reads:** Read results MUST NOT reconstruct facts not explicitly persisted. Speculation = epistemic containment breach.

---

## 5. 🗺️ Architecture & Module Map

### Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Language** | Python 3.10–3.13 |
| **Database** | SQLite + `sqlite-vec` (vector search), `aiosqlite` (async) |
| **Embeddings** | `sentence-transformers` + ONNX Runtime |
| **Crypto** | `cryptography` (Ed25519, AES-GCM) + `hashlib` (SHA-256 ledger, SHA3-256 taint) + `keyring` (OS-native vault) |
| **API / CLI** | FastAPI + Uvicorn (`[api]`) / Click + Rich |
| **Cloud (Opt)** | `asyncpg` (AlloyDB), `redis` (L1 cache), `qdrant-client` (vector cloud) |
| **Lint / Type** | Ruff (`E,F,W,I,UP,B,G,TID`, len=100) / Pyright (basic) |
| **Testing** | `pytest` + `pytest-asyncio` + `pytest-cov` + `pytest-xdist` |

### Module Map — `cortex/` (58 subdirectories)

Grouped by domain. Risk level governs the care required before modification.

#### 🔴 CRITICAL — State Mutation & Trust

| Module | Purpose | Key Files |
| :--- | :--- | :--- |
| `engine/` | Core CRUD, Kinetic Engines (EntropyAnnihilator, AutoCrystallizer), fact store, causal scheduler | `crystallizer.py`, `entropy.py`, `synthesis.py`, `causal/taint_engine.py` |
| `audit/` | Master Ledger — immutable hash-chain for all actions | `ledger.py` |
| `ledger/` | Ledger origin tracking, public export, verifier utilities | `origin.py`, `public_export.py`, `public_verifier_utils.py` |
| `guards/` | Admission, contradiction, dependency, sovereign seals, ZK guard | `sovereign_seals.py`, `virgo.py`, `zk_guard.py` |
| `memory/` | Large public API surface for fact persistence and retrieval | — |
| `migrations/` | Schema evolution — irreversible production impact | — |
| `crypto/` | Key management (Ed25519), AES encryption, OS keyring integration | `keys.py`, `aes.py` |

#### 🟠 HIGH — External Contracts & Validation

| Module | Purpose |
| :--- | :--- |
| `verification/` | Formal or deterministic validation surfaces |
| `routes/` | External API contract (FastAPI). Must remain typed and stable. |
| `security/` | Security policies and enforcement |
| `consensus/` | Merkle trees, vote ledger, multi-agent consensus |
| `forensics/` | Forensic analysis and investigation tools |
| `auth/` | Authentication manager, token handling |
| `facts/` | Fact type definitions and management |

#### 🟡 MEDIUM — Services & Infrastructure

| Module | Purpose |
| :--- | :--- |
| `cli/` | Thin wrappers only. **No business logic.** |
| `api/` | API layer configuration and middleware |
| `services/` | Business logic services |
| `database/` | Database connection and session management |
| `storage/` | Storage abstraction layer |
| `cache/` | Redis L1 cache integration |
| `embeddings/` | Local embedding generation (ONNX) |
| `search/` | Search index and query execution |
| `semantic/` | Semantic analysis and matching |
| `telemetry/` | Metrics, tracing, observability |
| `observability/` | Prometheus, structured logging |
| `types/` | Shared type definitions and models |
| `core/` | Core utilities and base classes |
| `utils/` | General-purpose helpers |
| `config.py` | Configuration loading |

#### 🔵 EXTENSIONS & AGENTS — Modular Capabilities

| Module | Purpose |
| :--- | :--- |
| `extensions/` | Plugin ecosystem: `llm/`, `daemon/`, `swarm/`, `evolution/`, `security/`, `git/`, `gate/`, `ha/`, `bci/`, `encryption/`, `nexus/`, `policy/`, `cuatrida/` |
| `agents/` | Agent bus, planner, builtins (copilot), swarm orchestration |
| `swarm/` | Multi-agent dispatch and coordination |
| `mcp/` | MCP server implementation and mega-tools |
| `adk/` | Google Antigravity ADK runner |
| `gateway/` | API gateway and routing |
| `router/` | Internal request routing |
| `pipeline/` | Data processing pipelines |
| `events/` | Event bus and pub/sub |
| `context/` | Context window management |

#### ⚪ SPECIALIZED — Domain-Specific

| Module | Purpose |
| :--- | :--- |
| `compat/` | Backward compatibility shims |
| `compliance/` | EU AI Act compliance enforcement |
| `compaction/` | Fact pruning and compaction |
| `delivery/` | Content delivery |
| `enrichment/` | Data enrichment pipeline |
| `graph/` | Knowledge graph |
| `http/` | HTTP client utilities |
| `isa/` | Instruction set architecture |
| `mcts/` | Monte Carlo Tree Search |
| `production/` | Production deployment configuration |
| `runtime/` | Runtime kernel and lifecycle |
| `shannon/` | Information-theoretic analysis |
| `sica/` | SICA protocol |
| `simulation/` | Simulation environment |
| `worker/` | Background worker processes |
| `darknet/` | Adversarial network testing |
| `evm/` | Ethereum VM integration |
| `mac_maestro/` | macOS platform integration |

---

## 6. 🛠️ Development & Change Protocol

### 6.1 Environment Setup

```bash
pip install -e ".[all]"
pytest tests/ -v --cov=cortex
ruff check cortex/
pyright cortex/
uvicorn cortex.api:app --reload  # optional: API server
```

**Core Env Vars:** `GEMINI_API_KEY`, `CORTEX_DB_PATH`, `CORTEX_LOG_LEVEL`, `CORTEX_ENCRYPTION_KEY`, `HF_TOKEN`, `STRIPE_SECRET_KEY`, `REDIS_URL`, `DATABASE_URL`.

### 6.2 Coding Rules

1. **Type hints** on all public functions.
2. **Catch specific exceptions** only — no bare `except Exception:`.
3. Prefer **O(1) structures** (dicts/sets) over repeated O(N) scans.
4. **Use standard library first** — minimize dependencies.
5. Imports must remain **sorted and grouped** (Ruff enforces).
6. Tests should **mirror the `cortex/` structure**.

### 6.2.1 Coding Agent Hygiene (Jules / Sweep / Copilots)

To prevent PR review rejection and build failures:
1. **Never Stage/Commit Scratch Files:** Do not include throwaway scripts, temporary analysis files, or patch tools (e.g., `patch_*.py`, `test_*.py` in the root) in git commits. Ensure the workspace is clean before committing.
2. **Do Not Leave Blocking Debug Statements:** Avoid leaving synchronous blocks or loop stalls like `import time; time.sleep(0)` or `time.sleep(1)` inside production hot-paths or async event loops.
3. **Log Safely:** Do not replace `logger.info`, `logger.error`, or other structured loggers with bare `print()` statements in core modules.
4. **Preserve Language & Logic Verbatim:** During refactors, do not rewrite regexes, string formats, stop-word lists, or validation structures (such as Spanish character support `[a-záéíóúñ]` or crypto prefixes like `v6_aesgcm:`) unless explicitly prompted.

### 6.3 PR & Change Acceptance Gate

A change is **INCOMPLETE** if any applicable step is missing:

1. - [ ] **Tests** — coverage for modified or new behavior.
2. - [ ] **Typing** — explicit type hints on all public surfaces.
3. - [ ] **Migrations** — for schema changes: review `cortex/migrations/`, verify via `cortex/migrate.py`, document rollback target.
4. - [ ] **Trust Impact** — ledger/audit review for any guard, encryption, taint, or tenant isolation change.
5. - [ ] **Async Correctness** — no blocking calls, proper timeout/cancellation, resource cleanup.
6. - [ ] **Documentation** — update if public behavior, API contract, or CLI parity changes.

### 6.4 Multi-Session Handoff Protocol

```text
SESSION START:
  1. git log --oneline -10           → Reconstruct causal context from Git DAG (AX-041).
  2. Check Ledger for open_risks     → From previous session's emitted summary.
  3. Re-read Decision Gate §0        → Re-anchor constraints before any action.

SESSION END:
  Emit structured summary to Ledger:
  {
    agent_id:          <id>,
    session_id:        <id>,
    files_modified:    [<paths>],
    invariants_checked:[<list>],
    open_risks:        [<description>],
    next_action:       "<suggested continuation>"
  }

INVARIANT: Never assume prior session state. Always verify from Git DAG (AX-041).
```

---

## 7. 📂 Repository Navigation

### Key Documents

| Document | Path | Purpose |
| :--- | :--- | :--- |
| README | [`README.md`](README.md) | Project overview and install |
| Architecture | [`docs/architecture.md`](docs/architecture.md) | System topology and module map |
| Security & Trust | [`docs/SECURITY_TRUST_MODEL.md`](docs/SECURITY_TRUST_MODEL.md) | Trust boundaries, ledger, verification |
| Axioms | [`docs/AXIOMS.md`](docs/AXIOMS.md) | Full axiom documentation (AX series, Ω series) |
| Contributing | [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Contribution workflow |
| Operations | [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Runtime and maintenance |
| SDK Surface | [`docs/SDK-SURFACE.md`](docs/SDK-SURFACE.md) | Public API surface documentation |
| Developer Guide | [`docs/developer-guide.md`](docs/developer-guide.md) | Development workflow and patterns |

### Nested AGENTS.md

Domain-specific agent rules without inflating this root file:

| Path | Status | Scope |
| :--- | :---: | :--- |
| `cortex/engine/AGENTS.md` | ✅ Exists | Engine mutation rules (Annihilator/Crystallizer safety gates) |
| `cortex/memory/AGENTS.md` | 📋 Planned | Memory surface constraints (tenant isolation, fact aging) |
| `cortex/migrations/AGENTS.md` | 📋 Planned | Migration safety protocol |

**Rule:** Root AGENTS.md always takes precedence. Sub-files **augment** — never contradict.
