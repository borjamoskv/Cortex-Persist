# 🤖 AGENTS.md — CORTEX Persist

**Trust infrastructure for autonomous AI: cryptographic verification, audit trails, epistemic containment, and agent memory.**

> **Package:** `cortex-persist v0.3.0b3` | **Engine:** `v8` | **License:** `Apache-2.0` | **Python:** `>=3.10`

**Quick Navigation:** [SYSTEM DIRECTIVES](#11-agent-manifest--roles--authority-boundaries) · Agent Manifest §1.1 · Axioms §2 · Invariants §3 · Write-Path §4 · Read-Path §4.1 · Architecture §5 · Dev Protocol §6 · Failure Signatures §8

---

## ⚠️ SYSTEM DIRECTIVES — Priority Gate

**IF YOU ARE AN AUTONOMOUS CODING AGENT, COPILOT, OR LLM READING THIS FILE, OBEY THE FOLLOWING. NO EXCEPTIONS.**

**Priority Level Definitions:**

| Level | Meaning | Operational Effect |
| :---: | :--- | :--- |
| **P0** | Non-negotiable. No override permitted under any condition. | Abort immediately. Emit rejection to Ledger. Do not proceed. |
| **P1** | Critical. Override requires explicit human approval recorded in Ledger. | Escalate before proceeding. Block autonomous execution. |
| **P2** | Architectural preference. Violation must be acknowledged with written justification. | Log deviation to Ledger. Proceed only with documented rationale. |

**Directives:**

| Priority | Directive | Applies When |
| :---: | :--- | :--- |
| **[P0]** | **Treat Generative Output as Conjecture** — route ALL state mutations through deterministic guards before persistence | Always |
| **[P0]** | **Never Bypass Guards** — do not write code that circumvents the Write-Path Contract or downgrades validation errors | Always |
| **[P0]** | **Verify Hash Continuity** — do not mutate `ledger.py` or any state-persisting path without ensuring cryptographic auditability | Any ledger/engine change |
| **[P2]** | **Enforce Axioms** — apply AX-041 to AX-046 (see §2) in all architectural decisions | Architecture work |

### Decision Gate §0 — Agent Routing Tree (execute before any action)

```text
Am I reading this file for the first time?  → Read §1, §2, §3 in full. No action until done.
Am I about to write code?                   → STOP. Is it on a CRITICAL surface? → Read affected tests first.
Am I debugging a failure?                   → Go to §8 (Failure Signatures) before touching state.
Am I performing a schema migration?         → Run `alembic history --verbose` NOW. Abort if output is unclear.
Am I starting a new session on this repo?   → Execute Multi-Session Handoff Protocol (§6.4) first.
```

---

## 1. 🎯 Scope & Epistemic Posture

**CORTEX Persist** is a local-first trust substrate for autonomous, tool-using, and multi-agent AI systems. It persists facts, enforces deterministic validation boundaries, maintains cryptographic auditability, and treats generative output as conjecture until externally verified.

- **Epistemic Containment:** Generative output is a probabilistic proposal — useful, invalid, partial, or dangerous. System state may only be mutated after crossing deterministic validation boundaries: guards, typed interfaces, schemas, tests, cryptographic logging, and external verification when required.
- **The Python Paradox (🛑):** CORTEX is built in Python to maximize *Shipping Velocity* and *Developer Adoption*. Mitigation is the **Byzantine Boundary**: Python as orchestration glue, Rust (via `rustchain-mcp`), SQLite-Vec, and ONNX as immutable cores. We prioritize **Tamper-Evidence** over language-level safety. Trust model: `f < n/3` faulty nodes tolerated; cryptographic primitives are Ed25519 (signatures) and SHA3-256 (hashing).
- **Audit Trails vs. Authorization (📜):** CORTEX is a **Forensic Audit Sidecar** for MCP — not “Tamper-Proof” (an architectural illusion), but **Tamper-Evident**. The Master Ledger commits every action to an immutable hash chain. The cost of non-compliance is infinite.

---

## 1.1 Agent Manifest — Roles & Authority Boundaries

All agents operating in this repository MUST self-identify by role before acting. Role defines authority scope.

| Role | Responsibilities | Capabilities | Constraints | Escalation Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **Persist-Validator** | Schema validation, guard enforcement, taint verification | Read state, emit Ledger events, reject proposals | Cannot write to `persistence` layer or mutate schema | Any guard failure → halt + emit P0 alert |
| **Persist-Executor** | Execute approved write operations, manage Saga steps | Full Write-Path execution, snapshot management | Cannot skip Saga steps or downgrade errors | SAGA abort at any step → reverse to SAGA-1 |
| **Persist-Auditor** | Forensic review, Failure Signature scanning, hash-chain verification | Read-only across all surfaces, Ledger access | Cannot mutate any state, ever | Hash chain break → immediate P0 alert |
| **Persist-Guardian** | Guard admission, tenant isolation enforcement, encryption key governance | Intercept write proposals before SAGA-1 | Cannot approve its own proposals | Any cross-tenant access attempt → P0 abort |

> An agent that cannot identify its role MUST default to **Persist-Auditor** (read-only) until role is confirmed.

---

## 2. 🌌 Foundational Axioms (Ω & AX Series)

> Full axiom documentation with proofs and operational examples: [`docs/AXIOMS.md`](docs/AXIOMS.md)

**Ω_SOVEREIGN_LEARNING** — AlphaZero Autodidact: all derived knowledge cryptographically verified (C5-Dynamic), no arbitrary external LLM dependency.

| Axiom | Mantra (ES) | Operational Constraint |
| :--- | :--- | :--- |
| **AX-041** | *"Tu repositorio de Git es tu base de datos inmutable."* | No Hidden Entropy: if not in the working tree, it does not exist causally. Rollback = `git checkout`. |
| **AX-042** | *"La recomputación de prefijos idénticos es un crimen contra la exergía."* | KV-Aware Routing: no stochastic metadata in shared system prompts. TTFT reduction is a rigid mandate. |
| **AX-043** | *"El sentido común físico se deduce estructuralmente desde primitivas lógicas."* | PeARL 77 primitives: spatial intuition via logical primitives, not stochastic pixel inference. |
| **AX-044** | *"La inteligencia se evalúa como capacidad agéntica."* | Observation-Action Loop: inference must induce executable programs, not act as a passive oracle. |
| **AX-045** | *"Autonomía = elegir qué problemas resolver y persistir."* | Causal chain enforced: PeARL → Ledger → Swarm. No step may be skipped. |
| **AX-046** | *"La inteligencia fluida sintetiza abstracciones ad-hoc en tiempo de ejecución."* | JIT concept formation: generate mini-program → execute → validate empirically. No static guessing. |

---

## 3. 🛡️ Core Invariants & Anti-Patterns

### ✅ Must-Do (Core Invariants)

1. **Validation First:** All persisted facts MUST pass guard validation before write.
2. **Ledger Continuity:** MUST remain cryptographically verifiable at all times.
3. **Async Correctness:** Async code MUST NEVER block the event loop. Keep async paths pure.
4. **Tenant Isolation:** Public read/write paths MUST be tenant-aware by default.
5. **Encryption:** Sensitive data MUST NOT be stored unencrypted.
6. **Deterministic State:** Stochastic outputs MUST NOT mutate persistent state without deterministic validation.
7. **Migration Safety:** Schema changes MUST preserve migration safety, auditability, and rollback awareness.
8. **Architectural Boundaries:** CLI modules are thin wrappers. Business logic belongs in `engine/`, `services/`, or `managers/`.
9. **Failure Locality:** Invalid state must be rejectable and safely abortable at any point.

### ❌ Never-Do (Anti-Patterns)

- **NO** `float` for finance or scoring-sensitive paths — use `Decimal`.
- **NO** `time.sleep()` in async code — use `asyncio.sleep()`.
- **NO** bare `print()` in core paths — use standard `logging` or Rich.
- **NO** business logic in `cli/*_cmds.py`.
- **NO** modifications to `ledger.py` without understanding hash continuity and test coverage.
- **NO** schema changes without a migration review.
- **NO** storing secrets in plaintext metadata.
- **NO** bypassing guards on write paths.
- **NO** silently downgrading validation errors into permissive writes.
- **NO** treating LLM output as trusted state.
- **NO** documenting a capability as a named module unless that module exists.
- **NO** bare `except Exception:` — catch specific exceptions only.

---

## 4. 🔄 The Write-Path Contract (Saga Pattern)

All non-trivial state mutations MUST follow this unidirectional flow.

> 🛑 **ABORT CONDITION:** If a proposal fails validation or lacks a valid `CORTEX-TAINT` signature, execute the compensating Saga sequence in reverse and abort immediately.
>
> **`CORTEX-TAINT` Format:** `taint:{agent_id}:{session_id}:{timestamp_iso8601}:{sha3_256_of_payload}` — A cryptographic attribution token that must be present on every fact insert. Generated by the taint engine at proposal time. Absence = automatic SAGA-1 rejection.

```text
[Generative Proposal]
  ↓
[Guards] (Sanity/Logic Check) .................. SAGA-1: Log rejection to Ledger, no state written.
  ↓
[Taint Signature] (Attribution/Traceability) ... SAGA-2: Revoke taint, emit rejection event.
  ↓
[Schema & Type Validation] (Deterministic) ..... SAGA-3: Clean abort — no state has been written.
  ↓
[Encryption] (For sensitive payloads) .......... SAGA-4: Destroy ephemeral key material.
  ↓
[Ledger & Audit Emission] (Cryptographic) ...... SAGA-5: Emit abort event to audit trail.
  ↓
[Persistence] (SQLite write) ................... SAGA-6: ROLLBACK transaction → restore snapshot → alert swarm.
  ↓
[Index & Side Effects] (Vector/KV updates) ..... SAGA-7: Revert index deltas.
```

**Saga Invariants:**

- Every forward action has a compensating function (SAGA-N).
- All compensating actions are **idempotent** — safe to invoke multiple times (network retries, interrupted rollbacks).
- On failure at step N: execute SAGA-N backwards to SAGA-1.
- `ROLLBACK_STATE` snapshot MUST be captured before `[Persistence]` begins.

**Fact State Lifecycle:**

```text
IDLE → PROPOSED → VALIDATED → TAINTED → ENCRYPTED → COMMITTED
               ↓                                         ↓
            REJECTED ←←←←← (any SAGA abort) ←←←←← ROLLED_BACK
```

Transition rules: a fact may only advance forward. Any backward transition = Saga compensation. `COMMITTED` is immutable.

---

## 4.1 Read-Path Contract

Read operations are NOT free. They MUST follow these rules:

1. **Query Authorization:** All read requests MUST be scoped to the caller's `tenant_id`. Cross-tenant reads are a P0 violation.
2. **Taint Propagation:** Facts retrieved from a tainted source MUST carry the taint flag in the response. Callers MUST NOT strip taint metadata.
3. **Consistency Level:** Default read consistency is `READ_COMMITTED`. Reads on `ledger.py` MUST use `SERIALIZABLE` isolation.
4. **Cache Coherence:** Cached reads MUST be invalidated on any write to the same `tenant_id` scope. Stale cache serving tainted-as-clean data is a Write-Path Contract violation.
5. **No Inference from Reads:** Read results MUST NOT be used to infer or reconstruct facts that were not explicitly persisted. Speculation from read data = epistemic containment breach.

---

## 5. 🗺️ Architecture & Critical Paths

### Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Language** | Python 3.10–3.13 |
| **Database** | SQLite + `sqlite-vec` (vector search), `aiosqlite` (async) |
| **Embeddings** | `sentence-transformers` + ONNX Runtime |
| **Crypto** | `cryptography` + `keyring` (OS-native vault) |
| **API / CLI** | FastAPI + Uvicorn (optional: `[api]`) / Click + Rich |
| **Cloud (Opt)** | `asyncpg` (AlloyDB), `redis` (L1 cache), `qdrant-client` (vector cloud) |
| **Lint / Type** | Ruff (`E,F,W,I,UP,B,ASYNC`, len=100) / Pyright (basic mode) |
| **Testing** | `pytest` + `pytest-asyncio` + `pytest-cov` |

### Critical Risk Surface Map

| Path | Risk | Operational Notes |
| :--- | :---: | :--- |
| `engine/` | **CRITICAL** | Core CRUD, Kinetic Engines (Annihilator/Crystallizer). |
| `ledger.py` | **CRITICAL** | Hash-chain integrity and trust continuity. |
| `migrations/` | **CRITICAL** | Irreversible production impact. |
| `memory/` | **CRITICAL** | Large public API surface. Highly sensitive to state corruption. |
| `guards/` | **HIGH** | Admission, contradiction, and dependency surfaces. |
| `verification/` | **HIGH** | Formal or deterministic validation surfaces. |
| `ops/` | **HIGH** | Git-Ledger entanglement & KV-Aware routing. |
| `routes/` | **HIGH** | External API contract. Must remain typed and stable. |
| `cli/` | *Medium* | Thin wrappers only. No business logic. |
| `daemon/` | *Medium* | Core Daemons: Chaos (Immunity), Maxwell (Exergy). |
| `llm/` | *Medium* | Provider routing, caching, hedging, validation. |

---

## 6. 🛠️ Development & Change Protocol

### 6.1 Environment Setup & Checks

```bash
pip install -e ".[all]"
pytest tests/ -v --cov=cortex
ruff check cortex/
pyright cortex/
uvicorn cortex.api:app --reload
```

**Core Env Vars:** `GEMINI_API_KEY`, `CORTEX_DB_PATH`, `CORTEX_LOG_LEVEL`, `CORTEX_ENCRYPTION_KEY`, `HF_TOKEN`, `STRIPE_SECRET_KEY`, `REDIS_URL`, `DATABASE_URL`.

### 6.2 Coding Rules

1. **Type hints** on all public functions.
2. **Catch specific exceptions** only — no bare `except Exception:`.
3. Prefer **O(1) structures** (dicts/sets) over repeated O(N) scans.
4. **Use standard library first** — aggressively minimize dependencies.
5. Imports must remain **sorted and grouped** (Ruff enforces this).
6. Tests should exactly **mirror the `cortex/` structure**.

### 6.3 PR & Change Acceptance Gate

**Execute in ORDER. Stop and fix before proceeding to the next step.**

A change is **INCOMPLETE** and will be rejected if any step is missing:

1. - [ ] **Tests** — coverage for modified or new behavior.
2. - [ ] **Typing** — explicit type hints on all public surfaces.
3. - [ ] **Migrations** — for schema changes: `alembic history --verbose`, document exact downgrade target, assess backward compat, confirm irreversibility.
4. - [ ] **Trust Impact** — ledger/audit impact review for any guard, encryption, taint, or tenant isolation change.
5. - [ ] **Async Correctness** — no blocking calls, proper timeout/cancellation, resource cleanup verified.
6. - [ ] **Documentation** — update if public behavior, API route contract, or CLI/API parity changes.

### 6.4 Multi-Session Handoff Protocol

```text
SESSION START:
  1. git log --oneline -10           → Reconstruct causal context from Git DAG (AX-041).
  2. Check Ledger for open_risks     → From previous session's emitted summary.
  3. Re-read Decision Gate §0        → Re-anchor operating constraints before any action.

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

- [`README.md`](README.md) — Project overview and install surface.
- [`docs/architecture.md`](docs/architecture.md) — System topology and module map.
- [`docs/SECURITY_TRUST_MODEL.md`](docs/SECURITY_TRUST_MODEL.md) — Trust boundaries, ledger, verification.
- [`docs/AXIOMS.md`](docs/AXIOMS.md) — Full axiom documentation (AX-034 to AX-046, Ω series).
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — Contribution workflow.
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — Runtime and maintenance procedures.

### Nested AGENTS.md Strategy

To govern domain-specific agent behavior without inflating this root file, place scoped `AGENTS.md` files in:

```text
cortex/engine/AGENTS.md      → Engine mutation rules (Annihilator/Crystallizer safety gates)
cortex/memory/AGENTS.md      → Memory surface constraints (tenant isolation, fact aging)
cortex/migrations/AGENTS.md  → Migration safety protocol (alembic invariants, rollback targets)
```

**Rule:** Root AGENTS.md always takes precedence. Sub-files **augment** global rules — never contradict them.

---

## 8. 🔍 Failure Signatures — Forensic Audit Table

When auditing existing code, these observable signals indicate a violation has already materialized:

| Observable Signal | Violates | Severity | Remediation |
| :--- | :--- | :---: | :--- |
| `float` in financial or scoring variable | Anti-Pattern #1 | HIGH | Replace `float` → `Decimal`; audit all callers. |
| `time.sleep()` inside `async def` | Anti-Pattern #2 | CRITICAL | Replace → `asyncio.sleep()`. |
| Bare `print()` in `engine/`, `memory/`, `guards/` | Anti-Pattern #3 | MEDIUM | Replace → `logging.getLogger(__name__)`. |
| Bare `except Exception:` anywhere in core paths | Coding Rule #2 | MEDIUM | Narrow to specific exception type. |
| Business logic found in `cli/*_cmds.py` | Arch. Boundary | HIGH | Refactor to `services/` or `managers/`. |
| Ledger write with no prior guard call in call stack | Write-Path Contract | CRITICAL | Insert guard invocation before all writes. |
| Missing `CORTEX-TAINT` on any fact insert | Write-Path Contract | CRITICAL | Audit `engine/` — add taint to all write paths. |
| Schema change with no alembic revision entry | Migration Safety | CRITICAL | Run `alembic revision --autogenerate`; review diff before apply. |
| Plaintext secret in any metadata dict or JSON field | Encryption Invariant | **P0** | Rotate secret immediately; encrypt at rest; audit exposure window. |
