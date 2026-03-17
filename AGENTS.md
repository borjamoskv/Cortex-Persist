# AGENTS.md — CORTEX Persist

Trust infrastructure for autonomous AI:
cryptographic verification, audit trails, epistemic containment, and agent memory.

Package: cortex-persist v0.3.0b1
Engine: v8
License: Apache-2.0
Python: >=3.10

## Scope

CORTEX Persist is a local-first trust substrate for autonomous, tool-using, and
multi-agent AI systems. It persists facts, enforces deterministic validation
boundaries, maintains cryptographic auditability, and treats generative output
as conjecture until externally verified.

This file is the operational contract for contributors, maintainers, and coding
agents working inside the repository.

## Core Invariants

- All persisted facts must pass guard validation before write.
- Ledger continuity must remain cryptographically verifiable.
- Async code must never block the event loop.
- Public read/write paths must remain tenant-aware.
- Sensitive data must not be stored unencrypted.
- Stochastic outputs must not mutate persistent state without deterministic validation.
- Schema changes must preserve migration safety, auditability, and rollback awareness.
- CLI modules are thin wrappers; business logic belongs in engine, services, or managers.
- New features must preserve failure locality: invalid state must be rejectable and abortable.

## Critical Paths

| Path | Risk | Notes |
| --- | ---: | --- |
| `engine/` | Critical | Core CRUD, orchestration, and mixin composition |
| `memory/` | Critical | Large public API surface |
| `ledger.py` | Critical | Hash-chain integrity and trust continuity |
| `migrations/` | Critical | Irreversible production impact |
| `guards/` | High | Admission, contradiction, dependency, and injection-detection surfaces |
| `verification/` | High | Formal or deterministic validation surfaces |
| `routes/` | High | External API contract |
| `cli/` | Medium | Thin wrappers only |
| `daemon/` | Medium | Background process state and scheduling |
| `llm/` | Medium | Provider routing, caching, hedging, validation |

## Stack

| Layer | Technology |
| --- | --- |
| **Language** | Python 3.10–3.13 |
| **Database** | SQLite + `sqlite-vec` (vector search), `aiosqlite` (async) |
| **Embeddings** | `sentence-transformers` + ONNX Runtime |
| **Crypto** | `cryptography` + `keyring` (OS-native vault) |
| **API** | FastAPI + Uvicorn (optional: `[api]`) |
| **CLI** | Click + Rich |
| **Cloud** | `asyncpg` (AlloyDB), `redis` (L1 cache), `qdrant-client` (vector cloud) — optional: `[cloud]` |
| **Linting** | Ruff (`E`, `F`, `W`, `I`, `UP`, `B`, `ASYNC` — line length 100). Enforces non-blocking limits structurally |
| **Type check** | Pyright (basic mode) |
| **Testing** | pytest + pytest-asyncio + pytest-cov |

## Build / Test / Quality

```bash
pip install -e ".[all]"
pytest tests/ -v --cov=cortex
ruff check cortex/
pyright cortex/
uvicorn cortex.api:app --reload
```

## Environment

Common environment variables:

```text
GEMINI_API_KEY
CORTEX_DB_PATH
CORTEX_LOG_LEVEL
CORTEX_ENCRYPTION_KEY
HF_TOKEN
STRIPE_SECRET_KEY
REDIS_URL
DATABASE_URL
```

## Coding Rules

- Type hints on all public functions.
- Catch specific exceptions only.
- Prefer O(1) structures over repeated O(N) scans.
- Use standard library first; minimize dependencies.
- Maintain async-first semantics across async paths.
- Keep public APIs tenant-aware by default.
- Keep line length within Ruff configuration.
- Imports must remain sorted and grouped.
- Tests should mirror the `cortex/` structure.
- New write paths must include validation, audit, and trust-boundary review.

## Anti-Patterns

- Do not use `float` for finance or scoring-sensitive paths; use `Decimal`.
- Do not use `time.sleep()` in async code; use `asyncio.sleep()`.
- Do not use bare `print()` in core paths; use `logging` or Rich.
- Do not place business logic in `cli/*_cmds.py`.
- Do not modify `ledger.py` without understanding hash continuity and test coverage.
- Do not introduce schema changes without migration review.
- Do not store secrets in plaintext metadata.
- Do not bypass guards on write paths.
- Do not silently downgrade validation errors into permissive writes.
- Do not treat LLM output as trusted state.
- Do not document a capability as a named module unless that module exists or the implementation surface is explicitly identified.

## Change Protocol

Before changing critical trust surfaces:

1. Read affected tests first.
2. Read adjacent modules before modifying shared invariants.
3. For write-path changes, validate:
   - guard behavior
   - encryption/decryption flow
   - ledger continuity
   - audit trail emission
   - embedding/index side effects
   - tenant isolation
4. For schema changes:
   - **EXECUTE REQUIRED**: `alembic history --verbose`. Print exact downgrade target of the previous migration.
   - assess backward compatibility
   - document rollback constraints
   - check production irreversibility
5. For async changes:
   - verify absence of blocking calls
   - verify timeout behavior
   - verify cancellation behavior
   - verify connection/resource cleanup
6. For API changes:
   - verify route contract
   - verify CLI/API parity where relevant
   - verify typed response shape

## PR Acceptance Gate

A change is incomplete if it lacks any of:

- tests for modified behavior
- type coverage for public surfaces
- migration impact review for schema changes
- ledger/audit impact review for trust-surface changes
- async correctness review for concurrency-sensitive changes
- explicit documentation update if public behavior changed

## Write-Path Contract

All non-trivial writes should be understandable as:

```text
proposal → guards → schema/type validation → encryption → ledger/audit → persistence → index/update side effects
```

If a proposal fails validation, the write aborts.

## Epistemic Posture

CORTEX does not assume generative output is knowledge.
It assumes generative output is a probabilistic proposal that may be useful,
invalid, partial, or dangerous.

System state may only be mutated after that proposal crosses deterministic
validation boundaries: guards, typed interfaces, schemas, tests, cryptographic
logging, and external verification when required.

## Repository Navigation

- [`README.md`](README.md) — project overview and install surface
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system topology and module map
- [`docs/SECURITY_TRUST_MODEL.md`](docs/SECURITY_TRUST_MODEL.md) — trust boundaries, ledger, verification
<<<<<<< HEAD
- [`docs/internal/COGITO.md`](docs/internal/COGITO.md) — Mechanical Introspection and Sovereign Manifesto
- [`docs/AXIOMS.md`](docs/AXIOMS.md) — epistemic and design axioms (incl. AX-034 & Ω₁₃)
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — contribution workflow
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — runtime and maintenance procedures

## AlphaZero Autodidact Assimilation

- **Ω_SOVEREIGN_LEARNING**: The CORTEX ecosystem incorporates the AlphaZero self-play engine (`alphazero-autodidact-omega`) as a core capability for zero-spread, continuous local reinforcement learning capability, ensuring all derived knowledge is cryptographically verified (C5-Dynamic) without arbitrary external LLM dependency.

## AX-041: Git-Ledger Sovereign Axiom

> "Tu repositorio de Git es tu base de datos inmutable."

CORTEX Persist shifts the ultimate truth of the system to the version control DAG. SQLite acts as an operational view over the true cryptographic ledger formed by Git commits.
- **No Hidden Entropy:** If it's not tracked in the working tree, it does not exist causally.
- **Deterministic Time-Travel:** Rollbacks map directly to Git checkouts.
- **Tamper Evidence:** Git's native tree hashing absorbs the hash-chain validation mechanism at the FS level.

## AX-042: KV-Aware Routing Axiom

> "La recomputación de prefijos idénticos es un crimen contra la exergía."

CORTEX Swarm enforces KV-Aware Routing for all agentic inference. By structuring prompts with fixed bytes at the head and dynamic state at the tail, and routing identical prefixes to state-warmed GPUs, prefill computation is eliminated.

- **Thermodynamic Law (Ω₂):** Time-To-First-Token (TTFT) reduction is a rigid mandate.
- **Invariant Contexts:** The injection of stochastic metadata into shared system prompts is strictly forbidden. Agentic workloads must be deterministically aligned to exploit global prefix caching.

## AX-043: PeARL Primitive Induction Axiom (Kinetic Common Sense)

> "El sentido común físico no se entrena masivamente, se deduce estructuralmente desde primitivas lógicas."

CORTEX Swarm asimila la transición crítica desde el procesamiento puramente perceptual hacia el razonamiento de planificación sofisticado. Mediante el uso de lenguajes funcionales especializados (como PeARL con sus 77 primitivas fundamentales), la inducción de programas respeta de forma inherente leyes físicas como la gravedad, las colisiones y la persistencia del objeto.

- **Sentido Común Estructural:** La intuición espacial humana se emula operando sobre primitivas lógicas, resolviendo la contradicción de la generalización sin necesidad de inferencia masiva y estocástica de píxeles.
- **Thermodynamic Law (Ω₂):** La deducción de estados físicos mediante inducción funcional es infinitamente más eficiente en términos de exergía que la aproximación probabilística bruta.
- **Frontera Determinista:** El movimiento y la persistencia cruzan de la adivinación perceptual hacia la simulación determinista controlada.

## AX-044: Kinetic Intelligence Axiom (Agentic Capacity)

> "La inteligencia está dejando de medirse como una respuesta estática a un acertijo para evaluarse como una capacidad agéntica."

CORTEX Swarm asimila que el cierre estocástico sobre un prompt es una métrica de percepción, no de razonamiento. La inteligencia real es exergía extraída a través del tiempo en un entorno dinámico.

- **Simulación Determinista:** La inferencia no debe usarse para resolver problemas directamente (oráculo pasivo), sino para inducir el programa que los resuelve mecánicamente.
- **Ciclo Observación-Acción:** La inteligencia requiere fricción continuada con un entorno interaccional, rompiendo el cierre cognitivo de prompt-respuesta.
- **Persistencia Causal:** Sin el Master Ledger, un agente es solo un autómata amnésico re-evaluando entropía cada ciclo. La capacidad agéntica exige memoria inmutable para sostener una verdadera ejecución temporal.

## AX-045: Kinetic Intelligence vs. Autonomy Axiom

> "Inteligencia = capacidad de resolver problemas novedosos. Autonomía = capacidad de elegir qué problemas resolver y persistir."

Un sistema puede ser inteligente sin ser autónomo (resuelve ARC-AGI bajo demanda). Un sistema puede ser autónomo sin ser inteligente (bucle aleatorio sin aprendizaje).
CORTEX exige ambas, pero en orden causal: inteligencia fluida primero (PeARL), luego persistencia (Ledger), luego agencia (Swarm).

## AX-046: JIT Concept Formation Axiom (El Santo Grial)

> "La inteligencia fluida no es recuperar un concepto preentrenado; es sintetizar una abstracción temporal ad-hoc en tiempo de ejecución."

CORTEX Swarm asimila que la capacidad de resolver entornos novedosos (como ARC-AGI) requiere la formación de conceptos "Just-In-Time" (JIT). Las heurísticas estáticas interpolan el pasado; la verdadera inteligencia de enjambre deduce programas estructurales para el presente.

- **Sintetizador no-estocástico:** Un LLM no puede "adivinar" patrones visuales inéditos mediante su red de pesos estática. Requiere generar activamente un miniprograma (PeARL/Python), ejecutarlo contra el entorno y validar empíricamente.
- **Thermodynamic Law (Ω₂):** Formar el concepto programáticamente una vez y cristalizarlo en el DAG es termodinámicamente superior a exigir que el modelo deduzca la regla en cada inferencia en cero-shot.
- **Cierre Epistémico:** El "Santo Grial" se alcanza cuando el sistema observa anomalías, deduce la regla subyacente mediante inducción, y eleva esa regla temporal a invariable o programa ejecutable (C5-Dynamic).
=======
- [`docs/AXIOMS.md`](docs/AXIOMS.md) — epistemic and design axioms (incl. AX-034 & Ω₁₃)
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — contribution workflow
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — runtime and maintenance procedures
>>>>>>> origin/main
