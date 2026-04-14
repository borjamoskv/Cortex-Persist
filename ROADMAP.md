# ROADMAP

> **Tamper-Evident Decision Lineage for AI Systems**
> *Updated: Spring 2026 · Package metadata in tree: `v0.3.0b3`*
> *Classification: Planning snapshot. This file tracks capability bands, not canonical release truth.*
> *Release truth lives in `pyproject.toml`; historical release notes live in `docs/changelog.md`.*

---

## ✅ Foundation Lineage — Delivered In The Current Package Line

**Local-First Sovereign Trust layer.**

- [x] **Tamper-evident Memory Engine** (SQLite + WAL + 384-dim ONNX Embeddings)
- [x] **Hash-Chained Ledger** (SHA-256 blocks for facts and decisions)
- [x] **Merkle Consensus** (Batch integrity checkpoints)
- [x] **AST Sandbox** (LLM code execution integrity without `eval()`)
- [x] **Privacy Shield** (11-pattern secret detection at ingress)
- [x] **Multi-tenant Core** (`tenant_id` at all storage layers)
- [x] **RBAC Engine** (4 roles, structured API access limits)

---

## 🔥 v0.4.0 — Next (Scale & Orchestration)

**From local Python daemon → Multi-agent network backbone.**

- [ ] **GraphQL API** — Planned. No in-tree GraphQL implementation under `cortex/`.
- [ ] **Distributed Event Bus** — Planned. SSE streams exist; distributed bus remains open.
- [ ] **JavaScript/TypeScript SDK** — Partial. A thin REST client exists under `sdks/js/`; broader SDK surface remains open.
- [ ] **Remote Qdrant Cluster Support** — Partial. Backend and router exist; end-to-end hardening remains open.
- [ ] **Redis L1 Cache** — Distributed working memory for lower TTFT latency.

---

## 🔮 v1.0.0 — Vision (Sovereign Cloud)

**Managed Enterprise Platform.**

- [ ] **PostgreSQL/AlloyDB backend** — Partial. Backend code exists; managed platform posture remains open.
- [ ] **Admin Web Dashboard** — React UI for memory management and cryptographically signed audit visualization.
- [ ] **Multi-node Federation** — Distributed clusters with Gossip protocol.
- [ ] **Dual Compliance Mode** — EU AI Act (Art. 12) + SOC 2 reporting pipelines.
- [ ] **Zero-Knowledge Encryption** — Memories encrypted at rest on hardware keys.

---

## Pricing Strategy (Cloud Roadmap)

| Tier | Price | Target |
| :--- | :--- | :--- |
| **Self-Hosted** | Free forever | On-prem, unlimited, community support. |
| **Pro** | $29/mo | Small agent ensembles, cloud database backends. |
| **Team** | $99/mo | Multi-agent enterprise consensus, 99.9% SLA. |

---

*Roadmap subject to Sovereign revision by borjamoskv.*
