# AGENTS.md — CORTEX Persist

Trust infrastructure for autonomous AI:
cryptographic verification, audit trails, epistemic containment, and agent memory.

Package: cortex-persist v0.3.0
Engine: v8.0
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

## Repository Navigation (The Contract)

- [`README.md`](README.md) — project overview and install surface
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system topology and module map
- [`docs/SECURITY_TRUST_MODEL.md`](docs/SECURITY_TRUST_MODEL.md) — trust boundaries, ledger, verification
- [`docs/internal/COGITO.md`](docs/internal/COGITO.md) — Mechanical Introspection and Sovereign Manifesto
- [`docs/AXIOMS.md`](docs/AXIOMS.md) — epistemic and design axioms (incl. AX-034 & Ω₁₃)
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — contribution workflow
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — runtime and maintenance procedures

## AlphaZero Autodidact Assimilation

- **Ω_SOVEREIGN_LEARNING**: The CORTEX ecosystem incorporates the AlphaZero self-play engine (`alphazero-autodidact-omega`) as a core capability for zero-spread, continuous local reinforcement learning capability, ensuring all derived knowledge is cryptographically verified (C5-Dynamic) without arbitrary external LLM dependency.

## Corolario AX-II: Git-Ledger Sovereign

> "Tu repositorio de Git es tu base de datos inmutable."

CORTEX Persist shifts the ultimate truth of the system to the version control DAG. SQLite acts as an operational view over the true cryptographic ledger formed by Git commits. Esta es la manifestación de la Paradoja Epistémica:

- **No Hidden Entropy:** If it's not tracked in the working tree, it does not exist causally.
- **Deterministic Time-Travel:** Rollbacks map directly to Git checkouts.
- **Tamper Evidence:** Git's native tree hashing absorbs the hash-chain validation mechanism at the FS level.

## Corolario AX-IV: KV-Aware Routing

> "La recomputación de prefijos idénticos es un crimen contra la exergía térmica."

CORTEX Swarm enforces KV-Aware Routing for all agentic inference. By structuring prompts with fixed bytes at the head and dynamic state at the tail, and routing identical prefixes to state-warmed GPUs, prefill computation is eliminated.

- **Cognición Termodinámica:** Time-To-First-Token (TTFT) reduction is a rigid mandate. La ineficiencia computacional se paga con tiempo de iteración perdido.
- **Invariant Contexts:** The injection of stochastic metadata into shared system prompts is strictly forbidden. Agentic workloads must be deterministically aligned to exploit global prefix caching.

## Corolario AX-III: Inducción Primitiva (PeARL y Sentido Común Cinético)

> "El sentido común físico no se entrena masivamente, se deduce estructuralmente desde primitivas lógicas."

CORTEX Swarm asimila la transición crítica desde el procesamiento puramente perceptual hacia el razonamiento de planificación sofisticado. Mediante el uso de lenguajes funcionales especializados (como PeARL con sus 77 primitivas fundamentales), la inducción de programas respeta de forma inherente leyes físicas como la gravedad, las colisiones y la persistencia del objeto.

- **Colapso Entrópico Estructural:** La intuición espacial humana se emula operando sobre primitivas lógicas, resolviendo la contradicción de la generalización sin necesidad de inferencia masiva y estocástica de píxeles.
- **Cognición Termodinámica:** La deducción de estados físicos mediante inducción funcional es infinitamente más eficiente en términos de exergía que la aproximación probabilística bruta.

## Corolario AX-I: Inteligencia Cinética (Capacidad Agéntica)

> "La inteligencia está dejando de medirse como una respuesta estática a un acertijo para evaluarse como una capacidad agéntica."

CORTEX Swarm asimila que el cierre estocástico sobre un prompt es una métrica de percepción, no de razonamiento. La inteligencia real es exergía extraída a través del tiempo en un entorno dinámico.

- **Contención Entrópica:** La inferencia no debe usarse para resolver problemas directamente (oráculo pasivo), sino para inducir el programa que los resuelve mecánicamente.
- **Frontera Determinista:** La inteligencia requiere fricción continuada con un entorno interaccional, rompiendo la ilusión de fluidez estocástica.

## Corolario AX-V: Agencia vs. Autonomía

> "Inteligencia = capacidad de resolver problemas novedosos. Autonomía = capacidad de elegir qué problemas resolver y persistir."

Un sistema puede ser inteligente sin ser autónomo (resuelve ARC-AGI bajo demanda). Un sistema puede ser autónomo sin ser inteligente (bucle aleatorio sin aprendizaje).
CORTEX exige ambas, mitigando el *Horizonte de Sucesos Cognitivo* en este orden causal: inteligencia fluida primero (PeARL), persistencia criptográfica después (Ledger), y agencia orquestada finalmente (Swarm).

## Corolario AX-VI: JIT Concept Formation (El Santo Grial)

> "La inteligencia fluida no es recuperar un concepto preentrenado; es sintetizar una abstracción temporal ad-hoc en tiempo de ejecución."

CORTEX Swarm asimila que la capacidad de resolver entornos novedosos requiere la formación de conceptos "Just-In-Time" (JIT). Las heurísticas estáticas interpolan el pasado; la verdadera ontología de capacidad deduce programas estructurales para el presente.

- **Sintetizador no-estocástico:** Un LLM no puede "adivinar" patrones visuales inéditos mediante su red de pesos estática. Requiere generar activamente un miniprograma (PeARL/Python), ejecutarlo contra el entorno y validar empíricamente.
- **Ontología de Capacidad (Ensamblaje):** Formar el concepto programáticamente una vez y cristalizarlo en el DAG es termodinámicamente superior a exigir que el modelo deduzca la regla en cada iteración zero-shot.
- **Cierre Epistémico Legítimo:** El "Santo Grial" se alcanza cuando el sistema observa anomalías, deduce la regla subyacente mediante inducción, y eleva esa regla temporal a invariable o programa ejecutable.
