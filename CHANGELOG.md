# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — v6.x (Sovereign Cloud)

### In Progress
- GraphQL API (`/graphql`) — cross-language integration layer
- Distributed Event Bus (NATS/Redis Streams) for swarm orchestration
- GCP deployment blueprints (AlloyDB + GKE + Qdrant Cloud)
- Zero-Knowledge encryption for agent memories at rest

---

## [6.0.0-alpha] — 2026-02-23

### Architecture
- **Multi-Tenancy**: Cryptographic data isolation at L1/L2/L3 — `tenant_id` enforced at all memory layers
- **RBAC Engine**: Four-role hierarchy (`SYSTEM`, `ADMIN`, `AGENT`, `VIEWER`) with 11 atomic permission scopes (e.g., `read:facts`, `write:facts`, `manage:keys`, `system:config`)
- **Distributed Backends**: AlloyDB (L3 target), Qdrant Cloud (L2), Redis (L1) as v6 standard backends
- **Tripartite Memory formalized**: L1 Working → L2 Vector → L3 Episodic Ledger, all tenant-scoped

### Security
- **SecurityHeadersMiddleware**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options on all API responses
- **ContentSizeLimitMiddleware**: Request body size capping to prevent DoS
- **Privacy Shield expanded**: 11 secret detection patterns (GitHub tokens, GitLab PATs, JWT, SSH keys, Slack tokens) with 3-tier scoring (Critical/Platform/Standard)
- **Zero-Trust Ingress**: Private key detection forces local-only storage backend regardless of config

---

## [5.1.0] — 2026-02-23

### Added
- **Sidecar Compaction Monitor** (`daemon/sidecar/`): Production-grade, independently deployable memory compaction service with ARQ, uvloop, malloc_trim, cgroups v2 PSI, circuit breaker, zero-trust sandboxing, and standalone Dockerfile
- **Notification Bus** (`cortex/notifications/`): Pluggable async event notification with Telegram and macOS adapters, severity filtering, and concurrent delivery
- **Self-Healing Daemon** (`daemon/core.py`): `MoskvDaemon` watchdog orchestrating 13 specialized monitors including `AutonomousMejoraloMonitor` and `SecurityMonitor`; auto-reinstantiates monitors after 3 failures.
- **Prometheus Percentile Histograms** (`metrics.py`): `p50/p95/p99` quantile rendering in standard Prometheus summary format
- **AST Structural Nesting Detection** (`mejoralo/scan.py`): Detects deeply nested Python AST structures (threshold: 8)
- **EdgeSyncMonitor**: Autonomous Turso edge synchronization daemon with CDC (Change Data Capture)
- **Source Provenance Tracking** (`_detect_agent_source`): Auto-detects calling AI agent from env vars, session IDs — every new fact has provenance

### Changed
- **Compaction Monitor refactored**: `asyncio` + `ProcessPoolExecutor` for non-blocking memory pressure sampling
- **`async/await` drift fixed**: `create_key`, `list_keys`, `revoke_key` in `admin.py` and `stripe.py` properly awaited
- **MEJORAlo score**: 78/100 (from ~60 at project start)

### Fixed
- `test_memory_manager.py`: `PytestRemovedIn9Warning` — removed `@pytest.mark.asyncio` from fixture (redundant with `asyncio_mode=auto` in pytest 9)
- File descriptor leaks in daemon test suite
- `api_keys` table not created before `test_bad_key_rejected` — `AUTH_SCHEMA` added to `ALL_SCHEMA`

---

## [5.0.0] — 2026-02-22

### Added
- **Weighted Byzantine Fault Tolerance (WBFT)**: Full Byzantine consensus with reputation decay, domain-specific vote multipliers, `_verdict_without_quorum` Elder Council
- **AST Sandbox** (`sandbox.py`): LLM-generated code parsed via AST before execution — prevents prompt-injection-to-RCE attacks
- **Zero-dep Telemetry** (`telemetry.py`): OpenTelemetry-compatible span tracing with no external dependencies
- **Semantic Router** (`thinking/semantic_router.py`): Intent-based LLM routing (coding/creative/analytical domains)
- **Privacy Shield** (`storage/classifier.py`): Regex-based secret detection at data ingress — 6 initial patterns
- **Centralized SQLite Factory** (`db.py`): Single source of truth for all DB connections — WAL mode + `busy_timeout=5s` + `foreign_keys=ON` enforced everywhere
- **Google ADK integration** (`adk/`): Native Google Agent Developer Kit runner with toolbox bridge
- **kimi-claw daemon architecture**: 24/7 autonomous daemon integration with Kimi K2.5
- **Episodic Memory CLI** (`cortex episodic`): `observe`, `recall`, `replay` commands
- **Timeline visualization** (`cortex timeline`): Visual temporal memory browsing
- **Time Tracking** (`cortex time`): WakaTime-like session time tracker
- **Autorouter** (`cortex autorouter`): AI model auto-selection daemon
- **Agent Handoff** (`cortex handoff`): Structured agent-to-agent context transfer protocol
- **SAP Integration** (`sap/`): RFC client, field mapping, sync logic
- **High Availability** (`ha/`): CRDT, Gossip protocol, Raft consensus stubs

### Changed
- **Monitor system refactored**: `daemon/monitors.py` → `daemon/monitors/` package (10 independent module files)
- **Error hierarchy expanded**: granular DB errors — connection pool exhaustion, locking, transaction failures
- **stdlib namespace conflicts resolved**: `platform.py → sys_platform.py`, `exceptions.py → errors.py`, `types.py → models.py`
- **Dead code purged**: 20 dead imports removed from engine, embeddings, consensus, ha packages
- **`__all__` added**: `consensus/__init__.py`, `ha/__init__.py` (10 re-exports each)

### Fixed
- `db_writer.py`: `BaseException` in transaction context manager — prevents `CancelledError` deadlock on async cancellation
- Monitor package `__init__.py` empty after package conversion — re-exports all 10 monitor classes
- Namespace conflicts blocking test collection
- `except Exception` tightened: 15 broad catches → specific types (`sqlite3.Error`, `OSError`, `ValueError`, `json.JSONDecodeError`)

---

## [4.2.0] — 2026-02-21

### Added
- **MEJORAlo v9.0 Engine** (`mejoralo/`): X-Ray 13D autonomous code quality scanner + 4-wave healing protocol
- **Knowledge Graph** (`graph/`): SQLite + Neo4j backends, pattern detection, graph RAG endpoint
- **Thought Orchestra** (`thinking/orchestra.py`): N-model parallel reasoning with fusion engine
- **Episodic Memory** (`episodic.py`, `episodic_boot.py`): Session snapshots, boot-time recall
- **Self-reflection engine** (`reflection.py`): Meta-cognitive session analysis
- **Obsidian vault sync** (`sync/obsidian.py`): Bidirectional note sync
- **GitOps sync** (`sync/gitops.py`): Git-based state management
- **Federation protocol** (`federation.py`): Cross-instance CORTEX federation

### Changed
- **Engine mixin architecture**: Full migration to `StoreMixin`, `QueryMixin`, `ConsensusMixin`, `SearchMixin`, `AgentMixin`
- **CQRS separation**: `engine/sync_read.py` vs `engine/sync_write.py` — clear reads/writes boundary

### Fixed
- Flake8 violations: 1,614 → 146 (−91%): C901 complexity, E128/E124 indentation, E303 blank lines, F401 unused imports
- MEJORAlo: auto-fix 23/26 Ruff violations

---

## [4.1.0] — 2026-02-20

### Added
- **Reputation-Weighted Consensus v2** (`consensus_votes_v2` table): Dual-table architecture with backward compat
- **Merkle tree checkpoints**: Periodic batch verification of ledger integrity — `merkle_roots` table
- **Prometheus metrics** (`metrics.py`): Memory, fact count, consensus latency, daemon health
- **Internationalization** (`i18n.py`): Adaptive repair, LLMManager singleton (memory leak fix)
- **Tips engine** (`tips.py`): Lazy-loaded JSON tips with thread-safe cache and `__slots__`

### Fixed
- `CortexEngine` import cycle: moved mixins to submodules
- Broad `except Exception` in 7 CLI modules → specific tuples

---

## [4.0.0] — 2026-02-18

### Added
- **Sovereign Engine**: New `CortexEngine` with modular mixin architecture (Store, Query, Consensus)
- **Consensus Layer**: Reputation-Weighted Consensus (RWC) for multi-agent fact verification
- **Immutable Ledger**: Hash-chained transaction log (`SHA-256`) with Merkle tree checkpoints
- **Temporal Facts**: Native `valid_from` / `valid_until` support on knowledge facts
- **MCP Server** (`mcp/`): Full Model Context Protocol implementation for AI agent integration
- **Async API**: High-performance FastAPI backend with connection pooling and async SQLite
- **Industrial Noir UI**: Dashboard with Cyber Lime (`#CCFF00`) and Abyssal Black (`#0A0A0A`) theme
- **Internationalization**: Localized error messages (en, es)
- **Python SDK** (`sdks/python/`): `pip install cortex-memory` public API
- **OpenAPI spec** (`openapi.yaml` — 70.5 KB): Full machine-readable API contract
- **CI/CD** (`ci.yml`): GitHub Actions pipeline with pytest + ruff

### Changed
- **License**: MIT → Business Source License 1.1 (BSL-1.1). Converts to Apache 2.0 on 2030-01-01.
- **Database**: Migrated all engine ops to `aiosqlite` (async-first)
- **Search**: Replaced legacy FTS with `sqlite-vec` + ONNX quantized embeddings (384-dim, MiniLM-L6-v2)

### Fixed
- Auth: 422 on missing `Authorization` header → now correctly returns 401
- API: Added missing `source` and `meta` fields to `StoreRequest` model
- Security: Rotated compromised credentials, enforced strict CORS policies

---

*Changelog maintained by MOSKV-1 v5 (Antigravity) · MEJORAlo Protocol*
