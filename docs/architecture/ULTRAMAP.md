# [C5-REAL] CORTEX-Persist — 10x Repository ULTRAMAP

> **Reality Level:** `C5-REAL` (Executable Repository Architecture Map)  
> **Aesthetic:** `Industrial Noir 2026`  
> **Codename:** *Singularity Topology*  
> **Modules:** 58 Domain Subdirectories

---

## 1. Global Topology: The Six-Layer Architectural Stack

The CORTEX-Persist codebase is structured into six discrete operational layers. Every state mutation is validated, cryptographically bound, and persisted across this pipeline.

```
                  ┌────────────────────────────────────────────────────────┐
                  │                      1. INTERFACE                      │
                  │       cli  ·  api  ·  routes  ·  mcp  ·  adk  ·  http    │
                  └───────────────────────────┬────────────────────────────┘
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                       2. SECURITY                      │
                  │   auth  ·  security  ·  guards  ·  compliance  ·  evm    │
                  └───────────────────────────┬────────────────────────────┘
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                         3. CORE                        │
                  │    engine  ·  memory  ·  facts  ·  database  ·  storage │
                  └───────────────────────────┬────────────────────────────┘
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                        4. TRUST                        │
                  │        audit  ·  ledger  ·  consensus  ·  verify       │
                  └───────────────────────────┬────────────────────────────┘
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                      5. COGNITION                      │
                  │  agents  ·  swarm  ·  context  ·  semantic  ·  shannon  │
                  └───────────────────────────┬────────────────────────────┘
                                              ▼
                  ┌────────────────────────────────────────────────────────┐
                  │                     6. PLATFORM/INFRA                  │
                  │  core  ·  types  ·  telemetry  ·  obs  ·  mac  ·  ext  │
                  └────────────────────────────────────────────────────────┘
```

---

## 2. Directory Taxonomy & Deep Module Specifications

### 2.1 Layer 1: Interface & Ingress (REST / CLI / IPC)

This layer handles external inputs, parsing developer queries, and formatting protocol frames.

| Directory | Core Responsibility | Primary Files / Handles | Inter-Module Dependencies |
| :--- | :--- | :--- | :--- |
| `cortex/api/` | FastAPI server bootstrap, middleware registry, lifespan controls. | `core.py`, `middleware.py`, `openapi.py` | `routes`, `auth`, `engine` |
| `cortex/routes/` | REST endpoint handlers exposing memory and trace contracts. | `facts.py`, `memories.py`, `ledger.py` | `api`, `services`, `types` |
| `cortex/gateway/` | Ingress gateway routing, telegram integrations, client validation. | `core.py` | `routes`, `security` |
| `cortex/router/` | Internal request router for local-first agent routing. | `core.py` | `core`, `engine` |
| `cortex/mcp/` | Model Context Protocol server exposing tools to Cursor/Windsurf. | `knowledge_watcher.py`, `server.py` | `engine`, `guards` |
| `cortex/adk/` | Google Antigravity (AGY) SDK execution agent runner. | `runner.py` | `agents`, `runtime` |
| `cortex/http/` | High-concurrency HTTP client utilities. | `client.py` | `utils` |
| `cortex/cli/` | Click CLI commands for developers, DB migration tools, and diagnostics. | `daemon_cli.py`, `facts_cmds.py` | `engine`, `services` |

---

### 2.2 Layer 2: Security & Governance (Guardrails / Isolation)

Ensures that executions respect tenant limits, compliance guidelines, and cryptography signatures.

| Directory | Core Responsibility | Primary Files / Handles | Inter-Module Dependencies |
| :--- | :--- | :--- | :--- |
| `cortex/auth/` | Authentication manager, token issuers, API Key hashing, RBAC. | `rbac.py`, `manager.py` | `database`, `types` |
| `cortex/security/` | Token quota rules, tenant isolation, fraud pattern recognition. | `quota.py`, `fraud.py` | `auth`, `telemetry` |
| `legacy_research/guards/` | Admission validators, cryptographic ZK guards, contradiction check. | `sovereign_seals.py`, `virgo.py` | `crypto`, `engine` |
| `cortex/compliance/` | EU AI Act compliance checks, inline redaction rules. | `pii_redactor.py` | `guards`, `routes` |
| `cortex/darknet/` | Adversarial penetration testing sandbox for prompt injection validation. | `adversary.py` | `guards`, `agents` |
| `cortex/evm/` | Ethereum VM integration for on-chain identity credentials. | `contract_bridge.py` | `crypto`, `auth` |

---

### 2.3 Layer 3: Memory & State Engine (KV / Vector / Graph)

Coordinates working memories, embedding generation, and persistent database mappings.

| Directory | Core Responsibility | Primary Files / Handles | Inter-Module Dependencies |
| :--- | :--- | :--- | :--- |
| `cortex/engine/` | Aggregated fact orchestrator (`CortexEngine`) via Mixin architecture. | `crystallizer.py`, `entropy.py` | `database`, `ledger`, `cache` |
| `cortex/memory/` | Tripartite Memory Stack (L1 Working, L2 Vector, L3 Event Ledger). | `manager.py`, `vector_providers/` | `cache`, `embeddings`, `database` |
| `cortex/facts/` | Domain definitions and serialization protocols for Fact states. | `models.py` | `types` |
| `legacy_research/database/` | SQLite WAL & Postgres connection pools and active adapter routing. | `pool.py`, `postgres_core.py` | `core`, `config` |
| `cortex/storage/` | Data persistence layers, parquet cold archiving, storage routers. | `postgres.py`, `parquet.py` | `database`, `types` |
| `cortex/cache/` | Redis L1 caching layer with automatic query coherence. | `redis_client.py` | `config` |
| `cortex/embeddings/` | Local ONNX embedding generations and transformer batching. | `onnx_runtime.py` | `config` |
| `cortex/search/` | Hybrid search engine fusing SQLite FTS5 index and vector models. | `hybrid.py` | `memory`, `database` |
| `cortex/graph/` | Epistemic knowledge graph mapping relationships. | `graph_core.py` | `memory`, `facts` |
| `cortex/compaction/` | Pruning agents, circadian sleep-mode memory consolidations. | `pruner.py` | `engine`, `database` |
| `cortex/enrichment/` | Async summarization of agent execution steps. | `summarizer.py` | `engine` |

---

### 2.4 Layer 4: Trust, Ledger & Cryptography (Verification)

Ensures that every write contains a cryptographic proof trail (`CORTEX-TAINT`).

| Directory | Core Responsibility | Primary Files / Handles | Inter-Module Dependencies |
| :--- | :--- | :--- | :--- |
| `legacy_research/audit/` | Master Ledger — immutable SHA-256 hash-chain mapping database writes. | `ledger.py` | `database`, `crypto` |
| `cortex/ledger/` | Origin validation metadata, ledger state verification, exports. | `origin.py`, `public_export.py` | `audit`, `crypto` |
| `cortex/consensus/` | Byzantine fault tolerance (BFT) vote ledger and consensus protocols. | `merkle.py`, `byzantine.py` | `ledger`, `database` |
| `cortex/crypto/` | Key generation (Ed25519), AES-GCM encryption, native Keyring wraps. | `keys.py`, `aes.py` | `utils` |
| `cortex/verification/` | Formal verification of Merkle continuity. | `validator.py` | `consensus`, `ledger` |

---

### 2.5 Layer 5: Cognition & Orchestration (Agent Swarms)

Manages multi-agent execution, planning loops, and semantic routing matrices.

| Directory | Core Responsibility | Primary Files / Handles | Inter-Module Dependencies |
| :--- | :--- | :--- | :--- |
| `cortex/agents/` | Agent registration, task planner loop, Hermes copilot runtime. | `planner.py`, `copilot.py` | `engine`, `runtime` |
| `cortex/swarm/` | Sovereign Swarm coordination, BFT voting, quorum sensing. | `orchestration.py` | `agents`, `consensus` |
| `cortex/context/` | Dynamic window context consolidation, token-budget calculations. | `window.py` | `types`, `engine` |
| `cortex/semantic/` | Semantic routing matrices for intent classifications. | `router.py` | `embeddings` |
| `cortex/shannon/` | Information entropy calculations on telemetry trace data. | `shannon_core.py` | `telemetry` |
| `cortex/sica/` | SICA cognitive protocol, BCI inputs. | `sica_bridge.py` | `core` |
| `cortex/simulation/` | Simulated environment for agent execution benchmarks. | `env.py` | `agents` |
| `cortex/mcts/` | Monte Carlo Tree Search for planning routes. | `tree_search.py` | `agents` |
| `cortex/worker/` | Background task worker execution loops. | `task_worker.py` | `database` |

---

### 2.6 Layer 6: Platform & Infrastructure

Low-level abstractions, platform telemetry, migrations, and extensions.

| Directory | Core Responsibility | Primary Files / Handles | Inter-Module Dependencies |
| :--- | :--- | :--- | :--- |
| `cortex/core/` | Base classes, configuration bindings. | `config.py` | None |
| `cortex/types/` | Shared models, dataclasses, protocols. | `models.py` | None |
| `cortex/utils/` | I18n translation engine, string normalizers, UUID formatters. | `i18n.py`, `canonical.py` | None |
| `cortex/telemetry/` | Zero-dependency OpenTelemetry instrumentation. | `tracing.py` | `utils` |
| `cortex/observability/` | Prometheus exporter, structured logger formats. | `prometheus.py` | `telemetry` |
| `cortex/migrations/` | Database schema migrations, target generation. | `001_initial.sql` | `database` |
| `cortex/compat/` | Backward compatibility shims. | `legacy_v4.py` | `core` |
| `cortex/production/` | Docker/K8s configuration setups. | `gunicorn.conf.py` | `api` |
| `cortex/runtime/` | Lifespan and execution cycle loop managers. | `kernel.py` | `core` |
| `cortex/mac_maestro/` | Native macOS notification and keychain adapters. | `maestro.py` | `utils` |
| `cortex/extensions/` | Third-party integrations, custom hypervisors, daemon tasks. | `hypervisor/`, `llm/` | `core`, `engine` |

---

## 3. Data Flow Lineage Model

### 3.1 Synchronous Write Execution (Saga Path)
```
[Client Call] 
     │
     ▼
[fastapi/routes] ────► [auth/rbac] (Validation)
                             │
                             ▼
                    [guards/sovereign_seals] (Verify input)
                             │
                             ▼
                    [engine/crystallizer] (Create CORTEX-TAINT)
                             │
                             ▼
                    [audit/ledger] (Log block to SHA-256 chain)
                             │
                             ▼
                    [database/pool] (SQLite WAL/Postgres transaction)
                             │
                             ▼
                    [cache/redis_client] (Invalidate cached reads)
```

### 3.2 Asynchronous Vector Compaction
```
[Circadian Cycle wake] 
     │
     ▼
[compaction/pruner] ──► [database/pool] (Scan for overflow facts)
                              │
                              ▼
                     [embeddings/onnx_runtime] (Compute 384-dim dense vectors)
                              │
                              ▼
                     [memory/vector_providers] (Flush to sqlite-vec / Qdrant)
```

---

## 4. Glosario Oficial y Taxonomía Semántica (Namespace Audit)

Para resolver las colisiones semánticas y alinear la ejecución, el siguiente glosario establece la jerarquía oficial:

*   **CORTEX-Persist**: El sistema base y la fortaleza inmutable.
*   **MOSKV-1 APEX**: La identidad activa y el operador lógico (Kernel).
*   **ULTRAMAP**: Estrictamente el sustrato espacial interno O(1) de coordenadas de los agentes y este mismo mapa arquitectónico. Nunca se usa para estrategias externas.
*   **CAUSAL-SIEGE**: La campaña y estrategia de infiltración de repositorios externos (Gatekeepers, SDKs de adopción viral).
*   **MOSKV-Sentinel**: El Gatekeeper Físico en CI/CD (GitHub Action) que rechaza la entropía estocástica externa.
*   **Sanedrín**: El demonio interno (`verify_sanedrin.py`) que audita el consenso BFT y la integridad del Ledger dentro de CORTEX.
*   **Estética C5-REAL**: Se mantiene el léxico brutalista ("Apoptosis", "Infección Estructural", "Troyano", "Cero Anergía") como ley física de comunicación, erradicando el "Green Theater" corporativo.
