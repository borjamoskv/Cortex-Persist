# CORTEX Roadmap

> **Sovereign Memory Engine for Enterprise AI Swarms**
> *Updated: 2026-02-23 · Status: v6 Alpha in active development*
> **Metrics:** 444 modules · 38 CLI commands · 787 lines of Arch documentation

---

## ✅ v4.x → v5.x — Done (Feb 2026)

**Foundation & Sovereignty** — Delivered in 8 days, 117+ commits.

- [x] Core memory engine (SQLite + WAL + embeddings)
- [x] Semantic search — MiniLM-L6-v2 (384-dim ONNX)
- [x] Multi-tenant API with auth (API key + JWT)
- [x] Thought Orchestra — N-model parallel reasoning
- [x] RAG endpoint (`/v1/ask`) with graph + vector hybrid
- [x] Merkle-based consensus & hash-chained ledger
- [x] Knowledge graph — SQLite + Neo4j backends
- [x] MEJORAlo code quality engine (X-Ray 13D, 4-wave healing)
- [x] MAILTV-1 autonomous email (Gmail API)
- [x] Agent missions, reputation system, vote ledger
- [x] Sovereign Gate — action approval framework
- [x] Python SDK (`pip install cortex-memory`)
- [x] OpenAPI spec (70.5 KB) + CI/CD pipeline
- [x] Self-healing daemon (10 monitors, auto-reinstantiation)
- [x] Tripartite Memory (L1 Working → L2 Vector → L3 Ledger)
- [x] Weighted Byzantine Fault Tolerance (WBFT) consensus
- [x] AST sandbox (LLM code execution safety)
- [x] Zero-dep telemetry layer (OpenTelemetry-compatible)
- [x] Privacy Shield — 11-pattern secret detection at ingress
- [x] Centralized SQLite factory (WAL + busy_timeout everywhere)
- [x] Sidecar Compaction Monitor (ARQ + uvloop + cgroups v2 PSI)
- [x] Notification Bus (Telegram + macOS adapters)
- [x] Source provenance auto-detection on all facts
- [x] Prometheus metrics with p50/p95/p99 histograms
- [x] Cross-platform support: macOS, Linux, Windows

---

## 🔥 v6.0 — Current (Q1-Q2 2026) — Sovereign Cloud

**The scale-up.** From single-user local daemon → enterprise multi-tenant cloud platform.

### Phase 1: Foundation *(In Progress)*
- [x] Multi-tenancy: `tenant_id` injected at all L1/L2/L3 layers
- [x] RBAC engine (4 roles, 4 permission scopes)
- [x] SecurityHeadersMiddleware (CSP, HSTS, X-Frame)
- [ ] **Full PostgreSQL/AlloyDB backend** — production L3 storage
- [ ] **Remote Qdrant cluster** — production L2 vector store
- [ ] **Redis L1 cache** — distributed working memory

### Phase 2: Orchestration *(Q2 2026)*
- [ ] **GraphQL API** — cross-language integration replacing REST where needed
- [ ] **Distributed Event Bus** — NATS or Redis Streams for swarm coordination
- [ ] **JavaScript/TypeScript SDK** — `npm install @cortex-memory/sdk`
- [ ] **Helm Chart** — Kubernetes production deployment
- [ ] **Streaming responses** — SSE for `/v1/ask` real-time output
- [ ] **Webhooks** — real-time event delivery to external systems

### Phase 3: Sovereign Cloud *(Q3 2026)*
- [ ] **GCP deployment blueprints** — AlloyDB + GKE + Qdrant Cloud + Cloud Run
- [ ] **Zero-Knowledge encryption** — user memories encrypted at rest, keys stay on hardware
- [ ] **Multi-node CORTEX federation** — distributed CORTEX clusters with Gossip protocol
- [ ] **Admin web dashboard** — React UI for memory management + audit visualization
- [ ] **Plugin system** — Slack, Discord, Notion, Linear importers

---

## 🔮 v7.0 — Vision (Q4 2026 - 2027)

**CORTEX Cloud** — Managed SaaS.

- [ ] **CORTEX Cloud** — Multi-region SaaS (eu-west, us-east, ap-southeast)
- [ ] **Team workspaces** — Shared sovereign memory with RBAC across teams
- [ ] **SOC 2 Type II** — Enterprise security certification
- [ ] **SOC 2 + EU AI Act** — Dual compliance (Art. 12 + SOC 2)
- [ ] **GraphQL** — Full alternative query interface
- [ ] **Mobile SDKs** — iOS (Swift) / Android (Kotlin) native integration
- [ ] **Vector DB portability** — Pinecone, pgvector, Weaviate backends
- [ ] **MCP Registry** — Shareable, versioned tool definitions

---

## Pricing Strategy

| Tier | Price | Target |
|:---|:---|:---|
| **Free** | $0/mo | Solo developers, local deployments |
| **Pro** | $29/mo | Small teams, cloud backends |
| **Team** | $99/mo | Companies, multi-agent consensus, SLA 99.9% |
| **Self-Hosted** | Free forever | On-prem, unlimited, community support |

---

## Current Status (2026-02-23)

| Metric | Value |
|:---|:---|
| Test functions | 1,162 |
| Production LOC | ~45,500 |
| Python Modules | 444 |
| CLI Commands | 38 |
| MEJORAlo score | 78/100 |
| CI status | ✅ Green |

---

*Roadmap maintained by MOSKV-1 v5 (Antigravity) · Subject to Sovereign revision*
