# Changelog

All notable changes to CORTEX, derived from the git history.

---

## [Unreleased] — Sovereign Overhaul (March 18, 2026)

### Added

- **Topología de Resiliencia en Cascada (Axioma Ω)**: Fallback automático a modelos locales o cloud gratuitos al agotar cuota (429), previniendo el colapso operativo.
- **Enrutamiento Cognitivo Dinámico**: Integración de `ReasoningMode` (`DEEP_THINK`, `DEEP_RESEARCH`, `ULTRA_THINK`) mapeado transparentemente a modelos de frontera.
- **Epistemic Circuit Breaker**: `SOVEREIGN_LOCK` con radar de entropía cognitiva para bloquear la escritura en el ledger si la máquina "alucina" o acumula errores constantes (`/circuit-breaker`).
- **Aislamiento Multi-Agente (Swarm Isolation)**: Despliegue automático de git worktrees y directorios de caché para aislar ejecuciones concurrentes sin bloqueos de BD.
- **Causality Deepening**: Propagación estricta de estado `TAINTED` en el Grafo Causal y Mutaciones.
- **CORTEX-Native Architecture**: Formalización de los Axiomas Ω₁₄ (Zero Friction) y Ω₁₅ (Execution Loops) en el RFC 01.

---

## v8.0.0 — Sovereign Cloud (February 24, 2026)

### Added

- **Documentation v6**: Complete rewrite — API, architecture, CLI, quickstart, deployment, security guides
- **Bicameral CLI**: Dual sync/async engine interface via Click
- **Admin route hardening**: Simplified config, hardened health checks
- **GitHub presence v8**: Branding, cortexpersist.com URLs, SECURITY.md, CONTRIBUTING.md, 14 topics

### Fixed

- Test suite stabilization: entropy, stripe webhooks, sync, tenant isolation
- Secret scanning alerts resolved (obfuscated test fixtures)

### Security

- Security headers middleware (CSP, HSTS)
- Input sanitization on all API routes
- Sentinel workflow for automated security scanning

---

## v6.0.0 — Multi-Tenant Architecture (February 20, 2026)

### Added

- **Multi-tenancy v6**: Full tenant isolation with RBAC (4 roles: admin, operator, reader, agent)
- **Sovereign Web UI**: New KETER and Apotheosis engines
- **GraphQL API** (preview)
- **Distributed event bus**
- **Qdrant vector store** integration
- **sqlite-vec** for local-first vector search (384-dim embeddings)
- **Privacy Shield**: 11-pattern secret detection on all ingress
- **AST Sandbox**: Safe LLM code execution
- **MEJORAlo daemon**: Background code quality monitoring
- **Context fusion** and canary security monitoring

### Architecture

- Tripartite memory: L1 (Redis/in-memory) → L2 (Qdrant/sqlite-vec) → L3 (SQLite/AlloyDB)
- Telemetry sidecars for observability
- Refactored crypto and authentication systems

---

## v5.1.0 — Stability & Hardening (February 23, 2026)

### Fixed

- Resolved stdlib namespace conflicts (`platform.py`, `exceptions.py`, `types.py`)
- Populated monitors package `__init__.py` (was empty, breaking daemon imports)
- P0 emergency stabilization (squashed)
- LEGIØN-1 PHALANX sweep: resolved 71 ruff issues across 302 files

### Improved

- MEJORAlo sovereign 130/100 purification
- Sanitized absolute paths for open-source transition
- Relaxed AST structural nesting threshold for advanced project architecture

---

## v4.0.0-alpha — Public Release (February 19, 2026)

### Added

- **Initial public release** on GitHub
- CortexEngine as core ledger for AI agents
- Modular mixin architecture (store, query, consensus, search, graph)
- SHA-256 hash-chained immutable ledger
- Merkle tree checkpoints
- WBFT (Weighted Byzantine Fault Tolerant) consensus
- MCP Server (Model Context Protocol)
- FastAPI REST API
- CLI with 38 commands
- Self-healing daemon with 13 monitors
- High Availability (Raft, Gossip, CRDT)
- 3-layer memory architecture
- Knowledge graph with pathfinding
- Federation module for cross-instance sync
- God Mode Orchestrator for perpetual self-improvement

### Infrastructure

- Docker support
- CI/CD via GitHub Actions
- Cross-platform (macOS, Linux, Windows)
- `pip install cortex-persist`

---

## v0.1.0 — Genesis (February 15, 2026)

- First commit: moskv-daemon with site monitoring, stale project detection, memory freshness alerts
- macOS notifications via launchd agent
- Dashboard card, CLI, and 16 unit tests
