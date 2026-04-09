# ROADMAP

> **Tamper-Evident Decision Lineage for AI Systems**
> *Updated: Spring 2026 · Status: 0.3.x beta in active development*
> *Classification: Planning snapshot. Current release truth lives in `CHANGELOG.md`; current product boundary lives in `docs/supported-core.md`.*

---

## ✅ 0.3.x Beta — Current (Foundation & Integrity)

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

- [ ] **GraphQL API** — Unified cross-language interface.
- [ ] **Distributed Event Bus** — Redis Streams for agent swarm coordination.
- [ ] **JavaScript/TypeScript SDK public release** — Promote the existing in-repo SDK to a published `npm` package with a stable support contract.
- [ ] **Remote Qdrant Cluster Support** — Moving Vector storage out of SQLite for massive scale.
- [ ] **Redis L1 Cache** — Distributed working memory for lower TTFT latency.

---

## 🔮 v1.0.0 — Vision (Sovereign Cloud)

**Managed Enterprise Platform.**

- [ ] **PostgreSQL/AlloyDB backend** — Centralized L3 storage.
- [ ] **Admin Web Dashboard** — React UI for memory management and cryptographically signed audit visualization.
- [ ] **Multi-node Federation** — Distributed clusters with Gossip protocol.
- [ ] **Dual Compliance Mode** — EU AI Act (Art. 12) + SOC 2 reporting pipelines.
- [ ] **Zero-Knowledge Encryption** — Memories encrypted at rest on hardware keys.

---

## Pricing Strategy (Cloud Roadmap)

This section is exploratory and non-contractual. It is not part of the supported-core promise and should not be read as an active commercial offer.

| Track | Current Intent | Contract Status |
| :--- | :--- | :--- |
| **Self-Hosted** | Keep a community-accessible operator-managed path | Not a paid support contract by default |
| **Future Cloud Evaluation** | Explore paid managed-service options once the supported core is proven in pilots | Roadmap only |
| **Future Team / Enterprise Plans** | Explore commercial packaging after publication, pilots, and support posture mature | Roadmap only |

---

*Roadmap subject to Sovereign revision by borjamoskv.*
