# AGENTS.md — CORTEX Persist

> **Trust Infrastructure for Autonomous AI**
> Cryptographic verification · Audit trails · EU AI Act compliance · AI agent memory
>
> `cortex-memory` **v0.3.0b1** · Apache-2.0 · Python ≥3.10

---

## Stack

| Layer | Technology |
| --- | --- |
| **Language** | Python 3.10–3.13 |
| **Database** | SQLite + `sqlite-vec` (vector search), `aiosqlite` (async) |
| **Embeddings** | `sentence-transformers` + ONNX Runtime |
| **Crypto** | `cryptography` + `keyring` (OS-native vault) |
| **API** | FastAPI + Uvicorn (optional: `[api]`) |
| **CLI** | Click + Rich |
| **macOS** | PyObjC (native notifications, Darwin-only) |
| **Cloud** | `asyncpg` (AlloyDB), `redis` (L1 cache), `qdrant-client` (vector cloud) — optional: `[cloud]` |
| **ADK** | `google-adk` ≥0.5.0 — optional: `[adk]` |
| **Billing** | `stripe` ≥8.0 — optional: `[billing]` |
| **Linting** | Ruff (`E`, `F`, `W`, `I`, `UP`, `B` — line length 100) |
| **Type check** | Pyright (basic mode) |
| **Testing** | pytest + pytest-asyncio + pytest-cov · **1993 tests**, 160 files |

---

## Architecture — Module Map

### 🧠 Core Engine

**`CortexEngine`** — composite orchestrator via mixin composition:

```python
class CortexEngine(StoreMixin, QueryMixin, MemoryMixin, TransactionMixin):
    """The Sovereign Ledger for AI Agents."""
```

Key methods: `store()`, `recall()`, `search()`, `hybrid_search()`, `graph()`, `prioritize()`, `shannon_report()`
All have `*_sync()` variants for blocking contexts.

| Module | Purpose |
| --- | --- |
| `engine/` | 43 files — mixins (`store_mixin`, `query_mixin`, `search_mixin`, `memory_mixin`, `ghost_mixin`, `privacy_mixin`, `transaction_mixin`, `agent_mixin`) + extensions (`apotheosis`, `mutation_engine`, `keter`, `nemesis`, `entropy`, `causality`) |
| `engine_async.py` | Async variant of the engine (standalone) |
| `core/` | Base data models, enums, constants |
| `types/` | Shared type definitions (`py.typed` — fully typed package) |
| `config.py` | Configuration management (env vars, defaults) |
| `facts/` | Fact type definitions and factories |
| `ledger.py` | Cryptographic ledger — tamper-proof hash chain for all facts |

#### Fact Model

```python
@dataclass
class Fact:
    id: int              # Auto-incremented
    tenant_id: str       # Multi-tenant isolation (default: "default")
    project: str         # Project namespace
    content: str         # AES-encrypted at rest, decrypted on read
    fact_type: str       # decision | error | ghost | bridge | discovery | axiom
    tags: list[str]      # JSON-serialized labels
    confidence: str      # C1 (hypothesis) → C5 (confirmed)
    valid_from: str      # ISO timestamp — when fact became active
    valid_until: str | None  # None = active, timestamp = deprecated
    source: str | None   # Origin (agent:gemini, human, cli, api)
    meta: dict           # AES-encrypted JSON metadata
    consensus_score: float  # Byzantine consensus weight (default: 1.0)
    created_at: str
    updated_at: str
    tx_id: int | None    # Transaction ID (for batched writes)
    hash: str | None     # Cryptographic hash chain link
```

#### Fact Lifecycle

```
Input → guard validation → AES encrypt(content, meta)
      → hash chain (ledger.py) → vector embed (sentence-transformers)
      → SQLite insert → audit log → signals/events dispatch
```

### 💾 Persistence

| Module | Purpose |
| --- | --- |
| `database/` | SQLite persistence layer with connection pooling |
| `storage/` | Pluggable storage backends (local, cloud) |
| `migrate.py` | Database migration runner |
| `migrations/` | SQL migration files (15 versions) |
| `compaction/` | Fact compaction, deduplication, entropy reduction |
| `sync/` | Cross-device synchronization (CRDT-based) |
| `ha/` | High-availability (leader election, replication) |

### 🔍 Intelligence (Semantic & Temporal)

| Module | Purpose |
| --- | --- |
| `embeddings/` | Vector embedding generation (`sentence-transformers` → ONNX) |
| `search/` | Semantic search over stored facts (`sqlite-vec` ANN) |
| `memory/` | High-level memory management API (38 files) |
| `graph/` | Knowledge graph — entity relationships & traversal |
| `episodic/` | Episodic memory subsystem (temporal sequences) |
| `shannon/` | Information-theoretic analysis (entropy, compression ratios) |
| `context/` | Context window management for LLM interactions |
| `songlines/` | Navigational memory pathways (spatial/temporal) |

#### Search Capabilities
- **Semantic Search**: Vector similarity via `sqlite-vec`
- **Text Search**: FTS5 text matching
- **Hybrid Search**: Reciprocal Rank Fusion (RRF) combining vector + text scores

### 🤖 Agent Infrastructure (Sovereign Swarm)

| Module | Purpose |
| --- | --- |
| `llm/` | LLM router (KETER-∞ ROP): Intent classification, Hedged Requests, EWMA Anycast |
| `agents/` | Multi-agent definitions and orchestration |
| `agent/` | Single-agent execution loop |
| `swarm/` | Multi-agent swarm coordination |
| `thinking/` | Reasoning chains and inference (10 files) |
| `perception/` | Environmental perception and sensor fusion |
| `evolution/` | Self-improvement, mutation engine, fitness evaluation (14 files) |
| `axioms/` | Foundational system axioms (Peano Soberano, Ω₀–Ω₆) |
| `skills/` | Agent skill registry and execution |
| `hive/` | Collective intelligence aggregation |
| `alma/` | Soul engine — personality and identity persistence |
| `definitions/` | LYNX-Ω, TOM, OLIVER — declarative agent roles (YAML) |

#### LLM Router Architecture (DNS Analogy)
The router implements a deterministic cascade to prevent capability degradation:
- **NegativeCache**: `NXDOMAIN` (skip known-dead providers)
- **PositiveCache**: `A-Record` (promote known-good providers)
- **HedgedRequests**: Race-to-first execution for `P99` latency reduction
- **Anycast**: EWMA-based latency tracking (fastest provider gets highest weight)
- **DNSSEC**: `IntentValidator` (post-response validation of semantic domain)

### 🔐 Security & Compliance (Zero Trust)

| Module | Purpose |
| --- | --- |
| `auth/` | Authentication (API keys, JWT, OAuth2) |
| `crypto/` | Cryptographic primitives (AES-256, Ed25519, hash chains) |
| `security/` | Threat feeds, anomaly detection, honeypots, integrity audit |
| `guards/` | Injection guards, contradiction guards, dependency guards, seals |
| `audit/` | Audit trail generation and compliance reporting |
| `gate/` | Admission control — policy enforcement before write |
| `policy/` | Declarative policy engine (ABAC, RBAC rules) |
| `immune/` | Immune system — anomaly detection, auto-quarantine |
| `red_team/` | Adversarial testing harness |
| `verification/` | Formal verification (Z3 solver integration) |

#### Defense in Depth
1. **Guards Layer**: `contradiction_guard`, `dependency_guard`, `injection_guard`
2. **Security Layer**: `anomaly_detector`, `threat_feed`, `integrity_audit`
3. **Ledger Layer**: `cryptography` hashes ensuring unalterable history

### 🌐 Integration & API (Model Context Protocol)

| Module | Purpose |
| --- | --- |
| `api/` | FastAPI application factory and middleware |
| `routes/` | REST API route handlers (24 files — full CRUD + search + admin) |
| `gateway/` | API gateway (request routing, auth middleware) |
| `mcp/` | Model Context Protocol server via `FastMCP` (SSE & stdio) |
| `adk/` | Google Agent Development Kit integration |
| `langbase/` | LangChain/LangBase adapter layer |
| `federation/` | Cross-instance federation (multi-node sync) |
| `consensus/` | Byzantine fault-tolerant consensus (7 files) |
| `platform/` | Platform-level abstractions (multi-tenant, billing hooks) |
| `browser/` | Browser automation integration |

#### MCP Tools Registered
- `cortex_store`: Store facts with intent validation
- `cortex_search`: Hybrid semantic search
- `cortex_status`: Memory metrics and stats
- `cortex_ledger_verify`: Full ledger hash chain verification
- `Mega Tools`: Aether, Void, Chronos paradigms

### 📡 Observability & Operations

| Module | Purpose |
| --- | --- |
| `telemetry/` | Metrics, traces, structured logging |
| `signals/` | Event bus, pub/sub, reactive signals |
| `events/` | Domain event definitions and dispatch |
| `notifications/` | macOS native notifications (8 files, Darwin-only) |
| `daemon/` | Background daemon process (46 files — scheduler, watchers, health) |
| `hypervisor/` | Process supervision, crash recovery, watchdog |
| `timing/` | Performance timing, SLA tracking |

### 🧪 Quality & DevEx

| Module | Purpose |
| --- | --- |
| `mejoralo/` | Sovereign code quality engine — scoring, linting, refactoring (18 files) |
| `moltbook/` | Interactive notebook / REPL environment (14 files) |
| `sap/` | SAP integration module (enterprise audit) |
| `vex/` | Vulnerability exchange format (security advisories) |
| `nexus/` | Cross-project pattern synchronizer |
| `cuatrida/` | Quad-dimensional analysis framework |
| `sovereign/` | Sovereign autonomy protocols (self-governance) |
| `launchpad/` | Project bootstrapping and scaffolding |
| `ui/` | Terminal UI components |

### 🔧 Utilities

| Module | Purpose |
| --- | --- |
| `utils/` | Shared utility functions (14 files) |
| `cli/` | Click-based CLI — 59 files (largest surface area) |
| `protocols/` | Protocol definitions (Python Protocol classes) |

---

## Entry Points

```text
cortex        → cortex.cli:cli          # Main CLI
moskv-daemon  → cortex.daemon_cli:main  # Background daemon
cortex-adk    → cortex.adk.runner:main  # Google ADK runner
```

---

## Build & Run

```bash
# Install — editable with all optional deps
pip install -e ".[all]"

# CLI operations
cortex --help
cortex store --type decision --source agent:gemini PROJECT "content"
cortex search "query" --limit 10
cortex export                              # Exports context snapshot

# API server
uvicorn cortex.api:app --reload

# Tests (1993 collected)
pytest tests/ -v --cov=cortex

# Quality
ruff check cortex/
pyright cortex/
```

### Optional dependency groups

| Extra | Installs | Purpose |
| --- | --- |---|
| `[api]` | FastAPI, Uvicorn, httpx | REST API server |
| `[dev]` | pytest, pytest-cov, pytest-asyncio, httpx, z3-solver | Development & testing |
| `[adk]` | google-adk | Google Agent Development Kit |
| `[toolbox]` | toolbox-core | Toolbox integration |
| `[billing]` | stripe | Payment processing |
| `[cloud]` | asyncpg, redis, qdrant-client | Distributed backends |
| `[all]` | All of the above | Full installation |

---

## Coding Conventions

1. **Type hints** on all public functions — Pyright basic mode enforced
2. **Async-first** — `async`/`await` everywhere, never block in async contexts
3. **O(1) lookups** — `dict`/`set` over O(N) list scans
4. **Specific exceptions** — no bare `except Exception`; catch `sqlite3.Error`, `OSError`, `ValueError`
5. **Standard library first** — minimize external deps
6. **Line length** — 100 chars (Ruff enforced)
7. **Imports** — sorted by Ruff (`I` rule): stdlib → third-party → local
8. **Tests** mirror `cortex/` structure in `tests/`
9. **Tenant-aware** — new data operations accept `tenant_id` (default: `"default"`)
10. **CORTEX-first** — decisions, errors, learnings persist to CORTEX DB

### File Naming

| Pattern | Convention |
|---|---|
| `*_mixin.py` | CortexEngine mixin modules |
| `*_cmds.py` | CLI command groups (Click) |
| `models.py` | Data models and types |
| `manager.py` | High-level orchestrator for a subsystem |
| `__init__.py` | Module exports (lazy-loaded via `__getattr__`) |

### Anti-Patterns (DO NOT)

- ❌ `float` for financial/scoring — use `Decimal`
- ❌ `time.sleep()` in async — use `asyncio.sleep()`
- ❌ Bare `print()` — use `rich.console` or `logging`
- ❌ Business logic in `cli/*_cmds.py` — those are thin wrappers
- ❌ Modify `ledger.py` without understanding the hash chain
- ❌ Skip tests for new mixins
- ❌ Add deps without `pyproject.toml` update
- ❌ Store secrets in `meta` dict without encryption

---

## Key Design Decisions

| Decision | Rationale |
| --- | --- |
| **Local-first** | All data in SQLite — no cloud dependency, works offline |
| **Privacy** | Zero telemetry, no external data transmission |
| **Cryptographic integrity** | Every fact is ledger-verified (hash chain) |
| **EU AI Act compliance** | Full audit trails for AI decisions |
| **O(1) in-process** | No HTTP overhead for memory operations |
| **Lazy imports** | `CortexEngine` + experimental modules load on first access |
| **pysqlite3 shim** | Allows newer SQLite versions with extension support |

### Experimental Modules (lazy-loaded)

```python
# Available via cortex.<name>, loaded on first access:
autopoiesis · circadian_cycle · digital_endocrine
epigenetic_memory · strategic_disobedience · zero_prompting
```

---

## File Ownership & Hot Paths

| Path | Touch Frequency | Risk | Notes |
|---|---|---|---|
| `engine/` | ⬆️ Very High | 🔴 Critical | Core CRUD — changes ripple to 90% of tests |
| `memory/` | ⬆️ Very High | 🔴 Critical | 38 files, largest module, public API surface |
| `llm/` | ⬆️ High | 🟡 Medium | Router, caches, hedged requests — fast-moving |
| `cli/` | ⬆️ High | 🟡 Medium | 59 files — user-facing, largest surface |
| `routes/` | ⬆️ High | 🟡 Medium | 24 endpoint files — REST API surface |
| `migrations/` | ⬇️ Low | 🔴 Critical | Schema changes are irreversible in production |
| `ledger.py` | ⬇️ Low | 🔴 Critical | Crypto integrity — any bug breaks trust chain |
| `daemon/` | ⬆️ Medium | 🟡 Medium | 46 files — background processes, complex state |

---

## Environment Variables

```bash
GEMINI_API_KEY           # Google Gemini API key (LLM operations)
CORTEX_DB_PATH           # Override DB location (default: ~/.cortex/cortex.db)
CORTEX_LOG_LEVEL         # DEBUG | INFO | WARNING | ERROR
CORTEX_ENCRYPTION_KEY    # AES-256 master key (auto-generated if missing)
HF_TOKEN                 # Hugging Face token (private embedding models)
STRIPE_SECRET_KEY        # Stripe billing (optional: [billing])
REDIS_URL                # Redis connection (optional: [cloud])
DATABASE_URL             # PostgreSQL/AlloyDB (optional: [cloud])
```

---

## Data Flow

```
┌─────────┐    ┌──────────┐    ┌────────────┐    ┌───────────┐
│  CLI    │───▶│  Engine  │───▶│  Guards    │───▶│  Crypto   │
│  API    │    │  (store) │    │  (validate)│    │  (encrypt)│
│  MCP    │    └──────────┘    └────────────┘    └─────┬─────┘
│  ADK    │                                           │
└─────────┘                                           ▼
                                              ┌───────────────┐
┌─────────┐    ┌──────────┐    ┌────────────┐ │   Ledger      │
│  Caller │◀───│  Engine  │◀───│  Embeddings│ │   (hash chain)│
│         │    │  (recall)│    │  (decode)  │ └───────┬───────┘
└─────────┘    └──────────┘    └────────────┘         │
                                                      ▼
                                              ┌───────────────┐
                                              │   SQLite       │
                                              │   + sqlite-vec │
                                              └───────────────┘
```

---

*CORTEX Persist · `cortex-memory` v0.3.0b1 · Updated 2026-03-02*
