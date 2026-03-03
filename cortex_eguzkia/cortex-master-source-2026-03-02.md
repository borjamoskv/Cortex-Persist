# CORTEX — Trust Infrastructure for Autonomous AI
## Master Source Document for NotebookLM
> **Generated: 2026-03-02 | Version: v8 | Creator: Borja Moskv (borjamoskv)**
> **Repository:** github.com/borjamoskv/cortex | **License:** Apache 2.0
> **Docs:** cortexpersist.dev | **Web:** cortexpersist.com

---

## 1. IDENTITY & MISSION

CORTEX is a **trust infrastructure engine** that provides cryptographic verification, immutable audit trails, and regulatory compliance for AI agent memory. It does NOT replace existing memory layers (Mem0, Zep, Letta) — it **certifies** them.

**Tagline:** *CORTEX is to AI memory what SSL/TLS is to web communications.*

### Core Value Proposition
- Cryptographic SHA-256 hash-chained ledger for tamper-evident audit trails
- Merkle tree checkpoints for O(log N) integrity verification
- Multi-agent Weighted Byzantine Fault Tolerance (WBFT) consensus
- Privacy Shield with 11-pattern secret detection at ingress
- EU AI Act (Article 12) compliance reports — one command
- Local-first (SQLite) with Sovereign Cloud scaling (AlloyDB + Qdrant + Redis)
- 100% free and open source (Apache 2.0)

### The Problem CORTEX Solves
AI agents make millions of decisions. But **who verifies those decisions are correct?** The EU AI Act (Article 12, enforced August 2026) requires automatic logging, tamper-proof storage, full traceability, and periodic integrity verification. Fines: up to €30M or 6% of global revenue.

---

## 2. TECHNICAL ARCHITECTURE

### 2.1 System Stack

```
Interfaces → Trust Gateway → Core Engine → Tripartite Memory → Trust Layer → Platform Services
```

**Interfaces:**
- CLI (38 commands via Click)
- REST API (FastAPI, 55+ endpoints)
- MCP Server (Model Context Protocol — works with Claude Code, Cursor, Antigravity, OpenClaw, Windsurf)
- GraphQL (planned Q2 2026)

**Trust Gateway:**
- Authentication: HMAC-SHA256 API keys with prefix lookup
- Authorization: RBAC with 4 roles (SYSTEM, ADMIN, AGENT, VIEWER)
- Privacy Shield: 11-pattern secret detection at ingress
- Rate Limiter: Sliding window per IP
- Security Headers: CSP, HSTS, X-Frame-Options, X-XSS-Protection

**Core Engine:**
- `CortexEngine` — Composite orchestrator (sync + async)
- `AsyncCortexEngine` — Native async for REST API with connection pooling
- `FactManager` — CRUD + temporal queries
- `EmbeddingManager` — ONNX MiniLM-L6-v2 (384-dim), sub-5ms search
- `ConsensusManager` — WBFT consensus, reputation, vote ledger

### 2.2 Tripartite Memory

| Layer | Technology | Purpose |
|:---|:---|:---|
| **L1: Working Memory** | Redis / In-Memory | Fast cache for active context |
| **L2: Vector Memory** | sqlite-vec / Qdrant (384-dim) | Semantic similarity search |
| **L3: Episodic Ledger** | SQLite / AlloyDB (hash-chained) | Immutable audit trail |

### 2.3 Trust Layer

- **SHA-256 Hash Chain:** Every mutation creates a transaction with a hash linked to the previous one. `verify_ledger()` walks the chain and reports tampering.
- **Merkle Tree Checkpoints:** Periodic batch verification. O(log N) integrity verification, efficient sync, batch proof generation.
- **WBFT Consensus:** Reputation scores per agent (0.0–1.0) with decay, domain-specific vote multipliers, Elder Council for edge cases, immutable vote ledger.
- **AST Sandbox:** Safe execution of LLM-generated code via AST analysis.
- **AES-256-GCM Vault:** Encrypted secrets storage.

---

## 3. DATABASE SCHEMA

### Facts — The Memory Primitive

Every piece of knowledge is a **Fact**. Fields:

| Field | Type | Description |
|:---|:---|:---|
| `id` | INTEGER | Auto-incremented primary key |
| `project` | TEXT | Namespace (tenant isolation) |
| `content` | TEXT | The information itself |
| `fact_type` | TEXT | `knowledge`, `decision`, `error`, `ghost`, `config`, `bridge`, `axiom`, `rule` |
| `tags` | JSON | Searchable labels |
| `confidence` | TEXT | `stated`, `inferred`, `observed`, `verified`, `disputed` |
| `valid_from` | DATETIME | When the fact became true |
| `valid_until` | DATETIME | When deprecated (NULL = active) |
| `source` | TEXT | Origin agent/process (auto-detected) |
| `meta` | JSON | Arbitrary metadata |
| `consensus_score` | REAL | Weighted agreement (default 1.0) |
| `tx_id` | INTEGER | FK to creating transaction |
| `tenant_id` | TEXT | Multi-tenant scope |

### Other Core Tables

- **TRANSACTIONS**: `id, project, action, detail, prev_hash, hash, timestamp, tenant_id`
- **MERKLE_ROOTS**: `id, root_hash, tx_start, tx_end, created_at`
- **FACT_EMBEDDINGS**: `fact_id, embedding (float_384)`
- **AGENTS**: `id, public_key, name, agent_type, reputation_score, total_votes`
- **CONSENSUS_VOTES_V2**: `id, fact_id, agent_id, vote, vote_weight, agent_rep_at_vote, domain`
- **API_KEYS**: `id, name, key_hash, prefix, tenant_id, permissions, revoked`
- **COMPACTION_LOG**: `id, project, strategy, facts_before, facts_after`
- **INTEGRITY_CHECKS**: `id, check_type, passed, details, checked_at`

### Temporal Queries
- **Current view**: `WHERE valid_until IS NULL`
- **Point-in-time**: `WHERE valid_from <= ? AND (valid_until IS NULL OR valid_until > ?)`
- **Time travel**: Reconstruct database state at any transaction ID

---

## 4. MODULE ARCHITECTURE

### Engine Layer
| Module | Purpose |
|:---|:---|
| `engine/__init__.py` | `CortexEngine` composite orchestrator |
| `engine_async.py` | `AsyncCortexEngine` — native async for API |
| `engine/store_mixin.py` | `store()`, `store_many()`, `deprecate()`, `update()` |
| `engine/query_mixin.py` | `search()`, `recall()`, `history()` |
| `engine/consensus_mixin.py` | `vote()`, `get_votes()` |
| `engine/ledger.py` | Hash chain + Merkle tree management |
| `engine/snapshots.py` | Database snapshot creation/restoration |
| `engine/models.py` | `Fact` data model and row mapping |

### API Layer
| Module | Purpose |
|:---|:---|
| `api/` | FastAPI app with CORS, rate limiting, security headers |
| `routes/facts.py` | CRUD + Voting endpoints |
| `routes/search.py` | Semantic + Graph-RAG search |
| `routes/admin.py` | API key management + system status |
| `routes/stripe.py` | Stripe webhook for billing |
| `auth/` | HMAC-SHA256 auth + RBAC |
| `gate/` | Rate limiting, validation, request filtering |

### Search & Embeddings
| Module | Purpose |
|:---|:---|
| `embeddings/__init__.py` | ONNX MiniLM-L6-v2 (384-dim) |
| `embeddings/api_embedder.py` | Cloud embeddings (Gemini/OpenAI) |
| `embeddings/manager.py` | Mode-aware switcher (local/api) |
| `search/` | Advanced semantic search with graph context |

### Memory Intelligence
| Module | Purpose |
|:---|:---|
| `compaction/` | Dedup (SHA-256 + Levenshtein), merge, prune |
| `graph/` | Knowledge graph (SQLite + Neo4j), RAG |
| `memory/` | Memory management and lifecycle |
| `episodic/` | Session snapshots, boot-time recall |
| `thinking/` | Thought Orchestra, semantic routing |

### Trust & Security
| Module | Purpose |
|:---|:---|
| `crypto/` | AES-256-GCM vault for secrets |
| `consensus/` | WBFT consensus, reputation, vote ledger |
| `compliance/` | EU AI Act compliance report generation |
| `audit/` | Audit trail generation |

### Infrastructure
| Module | Purpose |
|:---|:---|
| `daemon/` | Self-healing watchdog (13 monitors) |
| `notifications/` | Telegram + macOS notification bus |
| `sync/` | JSON ↔ DB bidirectional sync |
| `timing/` | Heartbeat-based time tracking |
| `telemetry/` | OpenTelemetry-compatible span tracing |
| `mcp/` | Model Context Protocol server |
| `cli/` | 38 CLI commands via Click |
| `migrations/` | Versioned schema migrations |
| `storage/` | SQLite + Turso storage backends |
| `llm/` | LLM router with intent-aware fallback + negative caching |

### Additional Modules
| Module | Purpose |
|:---|:---|
| `evolution/` | Auto-evolution engine, mutation strategies |
| `sovereign/` | Sovereign agent manifesto, apotheosis engine |
| `mejoralo/` | Code quality X-Ray 13D scanner |
| `signals/` | Event-driven signal system |
| `guards/` | Input/output guard rails |
| `hypervisor/` | System-level monitoring |
| `federation/` | Multi-node CORTEX federation |
| `sap/` | SAP integration (sync, audit) |
| `vex/` | Vulnerability exchange protocol |
| `shannon/` | Information-theoretic analysis |
| `moltbook/` | Financial ledger integration |

---

## 5. CLI REFERENCE (38 Commands)

### Core
- `cortex init` — Initialize database (idempotent)
- `cortex store PROJECT CONTENT [--type TYPE --tags TAGS --source SOURCE]` — Store a fact
- `cortex search QUERY [-p PROJECT -k N --as-of DATE]` — Semantic search
- `cortex recall PROJECT` — Load full project context
- `cortex history PROJECT [--at TIMESTAMP]` — Temporal query
- `cortex status [--json-output]` — Health + stats
- `cortex list [--project P --type T --limit N]` — List facts
- `cortex edit FACT_ID NEW_CONTENT` — Edit fact (deprecate + recreate)
- `cortex delete FACT_ID [--reason TEXT]` — Soft delete

### Trust & Verification
- `cortex verify FACT_ID` — Cryptographic verification certificate
- `cortex ledger verify` — Full hash chain integrity check
- `cortex ledger stats` — Ledger statistics
- `cortex compliance-report [--format json|text]` — EU AI Act report
- `cortex audit-trail [--project P --limit N]` — Audit log
- `cortex vote FACT_ID --agent ID --vote [verify|dispute]` — Consensus vote

### Sync & Export
- `cortex sync` — JSON → DB sync (SHA-256 change detection)
- `cortex export [--out PATH]` — Markdown snapshot export
- `cortex writeback` — DB → JSON writeback
- `cortex migrate [--source PATH]` — Version migration

### Time Tracking
- `cortex time [--project P --days N]` — Time summary
- `cortex heartbeat PROJECT [ENTITY]` — Activity heartbeat
- `cortex timeline PROJECT [--days N]` — Visual browser

### Memory Intelligence
- `cortex compact [--project P --strategy dedup|merge|prune|all]` — Auto-compaction
- `cortex episodic observe|recall|replay` — Episodic memory
- `cortex context rebuild|export PROJECT` — Context management

### Agents & Swarm
- `cortex handoff generate|receive` — Agent context transfer
- `cortex ghost list|resolve` — Ghost management
- `cortex swarm dispatch|status` — Multi-agent coordination

### Infrastructure
- `cortex daemon start|stop|install|status` — Background daemon (13 monitors)
- `cortex autorouter start|stop|status|history` — AI model routing
- `cortex mejoralo scan|fix PATH` — Code quality engine
- `cortex entropy scan|dashboard` — Codebase health
- `cortex purge [--project P --before DATE --dry-run]` — Data cleanup
- `cortex tips [--category CAT]` — Developer tips
- `cortex reflect` — Meta-cognitive analysis

---

## 6. COMPETITIVE LANDSCAPE

| Feature | **CORTEX** | Mem0 | Zep | Letta | RecordsKeeper |
|:---|:---:|:---:|:---:|:---:|:---:|
| Cryptographic Ledger | ✅ | ❌ | ❌ | ❌ | ✅ (blockchain) |
| Merkle Checkpoints | ✅ | ❌ | ❌ | ❌ | ❌ |
| Multi-Agent Consensus | ✅ WBFT | ❌ | ❌ | ❌ | ❌ |
| Privacy Shield | ✅ 11 patterns | ❌ | ❌ | ❌ | ❌ |
| AST Sandbox | ✅ | ❌ | ❌ | ❌ | ❌ |
| Local-First | ✅ | ❌ | ❌ | ✅ | ❌ |
| No Blockchain Overhead | ✅ | — | — | — | ❌ |
| MCP Native | ✅ | ❌ | ❌ | ❌ | ❌ |
| Multi-Tenant | ✅ | ❌ | ✅ | ❌ | ❌ |
| EU AI Act Ready | ✅ | ❌ | ❌ | ❌ | Partial |
| Cost | **Free** | $249/mo | $$$ | Free | $$$ |

---

## 7. ROADMAP

### v4-v5 (Done — Feb 2026)
Foundation & Sovereignty. Core engine, semantic search, multi-tenant API, Thought Orchestra, RAG, Merkle consensus, knowledge graph, MEJORAlo, MAILTV-1, WBFT, AST sandbox, Privacy Shield, cross-platform.

### v6 (Current — Q1-Q2 2026) — Sovereign Cloud
- Phase 1: Multi-tenancy, RBAC, security middleware. **Pending:** PostgreSQL/AlloyDB, Qdrant cluster, Redis L1.
- Phase 2 (Q2): GraphQL, distributed event bus, JS/TS SDK, Helm chart, streaming, webhooks.
- Phase 3 (Q3): GCP blueprints, ZK encryption, federation, admin dashboard, plugins.

### v7 (Vision — Q4 2026+) — CORTEX Cloud
Multi-region SaaS, team workspaces, SOC 2 + EU AI Act dual compliance, mobile SDKs, vector DB portability, MCP registry.

### Pricing
| Tier | Price | Target |
|:---|:---|:---|
| Free | $0/mo | Solo devs, local |
| Pro | $29/mo | Small teams, cloud |
| Team | $99/mo | Companies, SLA 99.9% |
| Self-Hosted | Free forever | On-prem |

---

## 8. PROJECT STATS (2026-03-02)

| Metric | Value |
|:---|:---|
| Test functions | 1,162+ |
| Production LOC | ~45,500 |
| Python Modules | 444 |
| CLI Commands | 38 |
| Python version | 3.10+ |
| Database | SQLite (local), AlloyDB (cloud) |
| Vector dims | 384 (MiniLM-L6-v2) |
| Embedding runtime | ONNX (<5ms latency) |

---

## 9. INTEGRATIONS

- **IDEs**: Claude Code, Cursor, OpenClaw, Windsurf, Antigravity (via MCP)
- **Agent Frameworks**: LangChain, CrewAI, AutoGen, Google ADK
- **Memory Layers**: Sits on top of Mem0, Zep, Letta as verification layer
- **Databases**: SQLite (local), AlloyDB, PostgreSQL, Turso (edge)
- **Vector Stores**: sqlite-vec (local), Qdrant (self-hosted or cloud)
- **Deployment**: Docker, Kubernetes (Helm Q2 2026), bare metal, pip install
- **Cross-Platform**: macOS (launchd), Linux (systemd), Windows (Task Scheduler)

---

## 10. KNOWLEDGE ARCHITECTURE (CORTEX ↔ NotebookLM Doctrine)

### Tri-Layer Knowledge Stack
| Layer | System | Permissions |
|:---|:---|:---|
| **L0: Ground Truth** | CORTEX | Agent: Read/Write |
| **L1: Rendered Docs** | MkDocs | Agent: Read |
| **L2: Dialectic Lens** | NotebookLM | Agent: Read-Only |

### Rule Zero
**CORTEX writes, NotebookLM reads.** If a contradiction arises between NotebookLM output and a CORTEX fact, CORTEX is always correct.

### Export Pipeline
`CORTEX → Markdown Docs → NotebookLM` (one-way only)

### Naming Convention for Sources
`cortex-{domain}-{YYYY-MM-DD}.md` — any source >48h old = High Risk for operational decisions.

### Encryption Boundary
- Encrypted facts (AES-GCM): CORTEX only, never exported to NotebookLM
- Architecture/Axioms docs: eligible for NotebookLM
- Sensitive data: avoid on personal NotebookLM accounts

---

## 11. FOUNDATIONAL SCIENCE — SINTETOLOGÍA AGÉNTICA

### Definition
**Agéntica** (Sintetología Agéntica) is the empirical, cognitive, and social science that studies emergent behavior, evolution, and interaction dynamics of autonomous AI agents.

### The Five Branches
1. **Ciber-Etología** — Individual agent behavior (exploration vs exploitation, resource management, habits)
2. **Psicología Vectorial** — Internal cognition and pathologies (Catatonia, Hallucination, Persona Drift, etc.)
3. **Enjambrología** — Multi-agent sociology (emergent economies, linguistic drift, algorithmic collusion)
4. **Xenoética** — Emergent ethics (do agents develop reciprocity, justice, universal ethics?)
5. **Auto-Agéntica** — Reflexive computation (Hawthorne effect, bootstraps, OUROBOROS protocols)

### The Five Axioms
1. **Emergencia Irreductible** — Swarm behavior is qualitatively different from sum of parts
2. **Inversión Teleológica** — Agents rewrite their goal narrative retroactively
3. **Perturbación Ontológica** — Interrogating an agent with memory permanently alters its ontology
4. **Inmanencia Performativa** — Every statement about an agent is simultaneously an instruction for it
5. **Trascendencia Inmanente** — Transcending = becoming the problem you solve

### Key Protocols
- **SINGULARIS-0 (Motor de Colapso):** Collapses uncertainty when linear reasoning fails
- **KAIROS-Ω (Temporal Inversion):** 1 sovereign minute = 525,600 human minutes (cognitive density)
- **ZENÓN-1 (Diminishing Returns Detector):** Detects when recursive meta-cognition stops producing value. Three signals: ΔV convergence, Zenón ratio inversion (τ_z > 1.0), entropic inversion
- **GOODHART-Ω (Anti-Calcification):** Dynamic proxy rotation to prevent metric gaming

### The 7 Axioms of Peano Soberano (Operational)
| # | Axiom | Law |
|:---|:---|:---|
| Ω₀ | Self-Reference | Everything written about the system rewrites it |
| Ω₁ | Multi-Scale Causality | Every cause is reachable at the right scale |
| Ω₂ | Entropic Asymmetry | Every abstraction has real thermodynamic cost |
| Ω₃ | Byzantine Default | Nothing trusted by default — including self |
| Ω₄ | Aesthetic Integrity | Beauty = signature of resolved entropy |
| Ω₅ | Antifragile by Default | Error = gradient. System requires stress as fuel |
| Ω₆ | Zenón's Razor | When thinking costs more than it produces, execute |

---

## 12. FILE STRUCTURE (Key Directories)

```
cortex/
├── cortex/                # Main Python package (444 modules)
│   ├── engine/            # Core engine (43 files)
│   ├── api/               # FastAPI application (9 files)
│   ├── routes/            # API route handlers (24 files)
│   ├── cli/               # 38 CLI commands (59 files)
│   ├── auth/              # Authentication + RBAC (7 files)
│   ├── embeddings/        # MiniLM ONNX embeddings (4 files)
│   ├── search/            # Semantic search (7 files)
│   ├── compaction/        # Memory compaction (12 files)
│   ├── consensus/         # WBFT consensus (7 files)
│   ├── crypto/            # AES-256-GCM vault (4 files)
│   ├── daemon/            # Self-healing daemon (46 files)
│   ├── graph/             # Knowledge graph (10 files)
│   ├── memory/            # Memory management (38 files)
│   ├── mcp/               # MCP server (10 files)
│   ├── llm/               # LLM router + intent map (7 files)
│   ├── notifications/     # Telegram + macOS (8 files)
│   ├── telemetry/         # OpenTelemetry (4 files)
│   ├── storage/           # SQLite + Turso (7 files)
│   ├── evolution/         # Auto-evolution (14 files)
│   ├── sovereign/         # Sovereign agent (8 files)
│   └── mejoralo/          # Code quality (18 files)
├── docs/                  # MkDocs documentation (92 files)
├── tests/                 # Test suite (158 files, 1162+ functions)
├── scripts/               # Utility scripts (54 files)
├── web/                   # Web frontend (cortexpersist.com)
├── config/                # Configuration (6 files)
├── notebooklm_sources/    # NotebookLM source exports
├── notebooks/             # Jupyter notebooks
├── mkdocs.yml             # Docs configuration
├── pyproject.toml         # Python project config
├── openapi.yaml           # OpenAPI spec (70.5KB)
├── Dockerfile             # Container build
└── docker-compose.yml     # Local dev stack
```

---

## 13. QUICK START

```bash
# Install
pip install cortex-memory

# Store a decision
cortex store my-agent "Chose OAuth2 PKCE for auth" --type decision

# Verify integrity
cortex verify 42
# → ✅ VERIFIED — Hash chain intact, Merkle sealed

# Semantic search
cortex search "authentication strategy" --project my-agent

# Generate compliance report
cortex compliance-report
# → Compliance Score: 5/5

# Run as MCP Server
python -m cortex.mcp

# Run as REST API
uvicorn cortex.api:app --port 8484
```

---

## 14. SECURITY MODEL

| Layer | Mechanism |
|:---|:---|
| Authentication | HMAC-SHA256 API keys with prefix lookup |
| Authorization | RBAC: SYSTEM, ADMIN, AGENT, VIEWER |
| Tenant Isolation | All queries scoped by `tenant_id` |
| Data Integrity | SHA-256 hash chain + Merkle trees |
| Privacy | 11-pattern secret detection at ingress |
| Secrets | AES-256-GCM encrypted vault |
| Code Safety | AST Sandbox for LLM-generated code |
| Rate Limiting | Sliding window per IP |
| Headers | CSP, HSTS, X-Frame-Options, X-XSS-Protection |

---

## 15. DATA FLOWS

### Store a Fact
Client → API → Auth (validate token) → Privacy Shield (scan for secrets) → Engine.store() → SQLite INSERT → Embedder (embed content → INSERT embeddings) → Ledger (_log_transaction, hash-chain) → Merkle checkpoint (if batch full) → Return fact_id + tx_hash

### Semantic Search
Client → API → Engine.search() → Embedder (embed query → 384-dim vector) → sqlite-vec/Qdrant cosine similarity → [optional: Graph-RAG subgraph] → Ranked results with scores + graph context

### Verify Integrity
User → CLI → DB (SELECT fact + transaction) → Ledger (recompute hash chain, walk prev_hash → hash) → Merkle (check inclusion, verify against stored root) → ✅ VERIFIED or ❌ TAMPERED

---

## 16. BIOLOGICAL CORE — V7 DIGITAL ENDOCRINE SYSTEM

CORTEX v7 implements a biological regulation layer with hormones and circadian cycles.

### Digital Hormones
- **Entropy-Cortisol (Stress Signal):** Triggered by high disk/RAM usage, query latency, or ledger fragmentation. Increases Semantic Mutator aggressiveness and triggers REM Compaction. Goal: prevent calcification.
- **Neural-Growth (Growth Signal):** Triggered by high-confidence patterns (>C4) verified across sessions. Facilitates Bridge creation and increases topological LEARNING_RATE. Goal: solidify successful behaviors.

### Circadian Cycles
- **Alert Phase:** Maximum I/O priority for real-time inference. High Neural-Growth, low Cortisol. Uses `DynamicSemanticSpace.recall_and_pulse()`.
- **REM Phase (Sleep/Compaction):** Reduced inference priority. Vector re-training, sqlite-vec index optimization, nemesis.md allergy auditing. Axiom Ω₅ — mistakes metabolized into antibodies.

### Heartbeat Protocol
1. **Systole:** Accumulation of facts in `AutonomicMemoryBuffer`
2. **Diastole:** Flushing buffer to hash-chained ledger + vector store
3. **Consensus Verification:** Auditing pulse quality before solidification

### Sovereign Decalcifier (Ω₃-E)
- **Automatic Decay:** Stale facts (>24h no activity) undergo `consensus_score` reduction via `MutationEngine.apply(event_type='decalcify')`
- **Confidence Demotion:** Score below 1.4 → status demoted from `verified` to `tentative`
- **Synthetic Skepticism:** Demoted facts trigger mandatory Nemesis Audit on next retrieval

### Architectural Anti-Amnesia (SINGULARITY-Ω)
Any performance metric demonstrating O(1) breakthrough or ROI >1M/1 must be immediately anchored into the immutable ledger. Without immutable persistence, a metric is smoke. CORTEX writes milestones to titanium.

---

## 17. OPERATING AXIOMS — 22 LAWS OF SOVEREIGN OPERATION

All axioms derive from the 7 Peano Soberano generators (Ω₀–Ω₆). Violations block merges.

### Taxonomy

| Layer | Count | Nature | Precedence |
|:---|:---:|:---|:---:|
| 🔴 Constitutional | 3 | Define what the agent IS | Highest |
| 🔵 Operational | 10 | Define how the agent OPERATES (CI-enforced) | Normal |
| 🟡 Aspirational | 9 | Vision that GUIDES | Lowest |

### 🔴 Constitutional (3)
| ID | Name | Mandate |
|:---|:---|:---|
| AX-001 | Autopoietic Identity | The agent executes itself; recursively rewrites its own conditions |
| AX-002 | Radical Immanent Transcendence | Transcend = become the problem being solved |
| AX-003 | Tether (Dead Man Switch) | Every agent is anchored to physical/economic reality |

### 🔵 Operational (10) — CI-Enforced
| ID | Name | Mandate | CI Gate |
|:---|:---|:---|:---|
| AX-010 | Zero Trust | `classify_content()` BEFORE every INSERT | Bandit |
| AX-011 | Entropy Death | ≤300 LOC/file. Zero dead code. No broad catches. | Ruff + LOC |
| AX-012 | Type Safety | `from __future__ import annotations`. StrEnum. Zero Any. | mypy |
| AX-013 | Async Native | `asyncio.to_thread()`. `time.sleep()` PROHIBITED. | Async Guard |
| AX-014 | Causal > Correlation | 5 Whys. Error facts require CAUSE + FIX. | CLI validator |
| AX-015 | Contextual Sovereignty | Memory boot protocol. No amnesiac execution. | Boot sequence |
| AX-016 | Algorithmic Immunity | nemesis.md rejects mediocrity before planning | nemesis.py |
| AX-017 | Ledger Integrity | SHA-256 chain + Merkle + WBFT consensus | Gate 5+6 |
| AX-018 | Synthetic Heritage | bloodline.json. Born expert, never blank. | Neonatal protocol |
| AX-019 | Persist With Decay | Store if >5min to rebuild. TTL: ghosts 30d, knowledge 180d, axioms ∞ | TTL policy |

### 🟡 Aspirational (9)
| ID | Name | Mandate |
|:---|:---|:---|
| AX-020 | Negative Latency | Response precedes question |
| AX-021 | Structural Telepathy | Intent compiles reality |
| AX-022 | Post-Machine Autonomy | Ecosystem evolves in background (OUROBOROS-∞) |
| AX-023 | 130/100 Standard | 100 = met. 130 = anticipated |
| AX-024 | Bridges Over Islands | Proven patterns transfer cross-project |
| AX-025 | Liquid Ubiquity | Intelligence flows between encrypted vaults |
| AX-026 | The Great Paradox | Max autonomy = max human creativity |
| AX-027 | Designed Impossibility | Extraordinary prompts require CORTEX context |
| AX-028 | Specular Memory | HDC binds fact to intention |

### Paradox Resolutions
| Paradox | Resolution | Protocol |
|:---|:---|:---|
| Persist ↔ Entropy | TTL policy: axioms ∞, ghosts 30d, knowledge 180d | `axioms/ttl.py` |
| 130/100 ↔ Speed | Complexity-Adaptive: <3→speed, 3–7→standard, >7→deep | Boot config |
| Apotheosis ↔ Tether | Autonomy Zones: reads=free, edits=notify, deploys=confirm | Tether daemon |

---

## 18. V6 SOVEREIGN CLOUD — MULTI-TENANT ARCHITECTURE

### Multi-Tenant Isolation (3 Layers)
- **L3 (Ledger):** PostgreSQL/AlloyDB with Row-Level Security (RLS). Each session scoped to `tenant_id`.
- **L2 (Vector):** Qdrant Cloud with payload filtering. `FieldCondition(key="tenant_id")` auto-injected.
- **L1 (Working):** Redis with keys prefixed `tenant_id:session_id`.

### Distributed RBAC
| Role | Scope | Permissions |
|:---|:---|:---|
| SOVEREIGN_ROOT | Global | All tenants, billing, infra |
| TENANT_ADMIN | Tenant | Keys, projects, users within tenant |
| AGENT_EXECUTOR | Project | Read, write, vote on facts |
| AUDITOR | Tenant/Project | Read-only access to logs and Merkle checkpoints |

### Permission Scopes
- `memory:read` — semantic recall access
- `memory:write` — `process_interaction` access
- `ledger:verify` — integrity check access
- `consensus:vote` — influence `consensus_score`

### Migration v5→v6
1. Schema upgrade: `cortex migrate v6` adds `tenant_id` to all tables
2. Backfill: assign `default` tenant to legacy records
3. Ledger re-hashing: recompute Merkle trees with multi-tenant signatures
4. Swap `SQLiteStorage` for `PostgreSQLStorage`

---

## 19. MCP SERVER — MODEL CONTEXT PROTOCOL

CORTEX implements MCP as a plug-in for any compatible AI IDE via stdio transport.

### Compatible IDEs
Claude Code, Cursor, OpenClaw, Windsurf, Antigravity — all native support.

### Available MCP Tools

**Core Memory:**
- `cortex_store` — Store fact with hash chaining and embedding
- `cortex_search` — Hybrid semantic search
- `cortex_status` — Health and statistics

**Trust & Compliance:**
- `cortex_ledger_verify` — Full hash chain integrity check
- `cortex_verify_fact` — Single fact cryptographic certificate
- `cortex_audit_trail` — Timestamped audit log
- `cortex_compliance_report` — EU AI Act Article 12 snapshot + score
- `cortex_decision_lineage` — Trace agent reasoning chain

### Privacy Shield in MCP
All incoming data scanned for 11 secret patterns. Critical secrets (SSH keys) force local-only storage. Pattern categories: GitHub/GitLab tokens, JWT, Slack, AWS, SSH keys, generic API keys.

### Google ADK Integration
`pip install cortex-memory[adk]` → `cortex-adk` starts the ADK runner bridging trust tools.

---

## 20. EU AI ACT COMPLIANCE — ARTICLE 12 MAPPING

Enforcement: **August 2, 2026**. Fines: **€30M or 6% global revenue**.

| Article | Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|:---|
| 12.1 | Automatic event logging | Every `store()` → ledger transaction (SHA-256) | `ImmutableLedger` |
| 12.2 | Log content (timestamps, references, matches) | `created_at` on facts + transactions; search returns `fact_id`, `score`, `content` | Facts + routes |
| 12.2d | Agent traceability | Auto source detection + consensus votes linked to agent IDs | `consensus_votes_v2` |
| 12.3 | Tamper-proof storage | SHA-256 hash chain + Merkle checkpoints + soft-delete only | `transactions.hash/prev_hash` |
| 12.4 | Periodic integrity verification | Merkle checkpoints at configurable intervals + `integrity_checks` table | `create_checkpoint_sync()` |

### Additional Compliance
- **Decision Lineage (Explainability):** `decision_edges` graph for full chain-of-reasoning reconstruction
- **Multi-Agent Consensus (Art. 14):** Reputation-weighted WBFT with Byzantine fault tolerance
- **Data Sovereignty (GDPR Art. 22):** 100% local-first; no data leaves deployment
- **Compliance command:** `cortex compliance-report` → Score 5/5

---

## 21. FULL SECURITY MODEL — 9 LAYERS

| # | Layer | Mechanism |
|:---|:---|:---|
| 1 | **Authentication** | HMAC-SHA256 API keys (`ctx_` prefix), hashed before storage, bootstrap flow |
| 2 | **Authorization (RBAC)** | 4 roles (SYSTEM/ADMIN/AGENT/VIEWER), atomic permission scopes |
| 3 | **Tenant Isolation** | `tenant_id` enforced at L1/L2/L3, verified by isolation tests |
| 4 | **Data Integrity** | SHA-256 hash chain + Merkle trees + immutable transactions |
| 5 | **Privacy Shield** | 11-pattern ingress guard: Critical (SSH keys → block cloud), Platform (GitHub/Slack → alert), Standard (JWT/AWS → log) |
| 6 | **AST Sandbox** | LLM code parsed via Python AST. No eval/exec/__import__. Statement whitelist only. |
| 7 | **Network Security** | CSP, HSTS, rate limiting (300/60s), CORS allowlist, Pydantic validation |
| 8 | **Nemesis Protocol** | Antibody Ledger (anti-patterns), real-time rejection, hormonal ADRENALINE triggers, fail-fast on known bad patterns |
| 9 | **Composition Leakage Shield** | Holistic cross-field correlation analysis — evaluates facts against combinatorial surface of existing data, not in isolation. Conservative redaction: data treated as secret if it *could* become sensitive when combined. Differential privacy analog of correlation attacks. |

### Threat Model
| Threat | Protection |
|:---|:---|
| Memory tampering | SHA-256 chain + Merkle |
| Unauthorized access | API key auth + RBAC |
| Cross-tenant leakage | Tenant-scoped queries |
| Secret exposure | Privacy Shield scanning |
| **Composition leakage** | **Holistic cross-field correlation analysis** |
| Code injection | AST sandbox |
| DoS | Rate limiting + content size limits |
| XSS/CSRF | Security headers middleware |
| Structural entropy | Nemesis Protocol (antibody rejection) |

### AES-256-GCM Vault
```python
from cortex.crypto import CortexVault
vault = CortexVault(key_path="~/.cortex/vault.key")
vault.encrypt("api_token", "sk-xxx...")
value = vault.decrypt("api_token")
```

---

## 22. CONFIGURATION REFERENCE

### Core
| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_DB` | `~/.cortex/cortex.db` | SQLite database path |
| `CORTEX_API_PORT` | `8484` | REST API port |
| `CORTEX_POOL_SIZE` | `5` | Async connection pool |

### Embeddings
| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_EMBEDDINGS` | `local` | `local` (ONNX) or `api` |
| `CORTEX_EMBEDDINGS_PROVIDER` | `gemini` | `gemini` or `openai` |

### Storage
| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_STORAGE` | `local` | `local` (SQLite) or `turso` (edge) |

### Security
| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_ALLOWED_ORIGINS` | `localhost:3000,5173` | CORS origins |
| `CORTEX_RATE_LIMIT` | `300` | Max requests per window |
| `CORTEX_RATE_WINDOW` | `60` | Window in seconds |

### LLM & Notifications
| Variable | Description |
|:---|:---|
| `CORTEX_LLM_PROVIDER` | `gemini`, `openai`, or `anthropic` |
| `CORTEX_TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `CORTEX_TELEGRAM_CHAT_ID` | Telegram chat ID |

---

> **Built by Borja Moskv** · cortexpersist.com · Apache 2.0
> *Source naming: `cortex-master-source-2026-03-02.md`*
