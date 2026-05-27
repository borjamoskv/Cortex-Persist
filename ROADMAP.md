# ROADMAP

> **Tamper-Evident Decision Lineage & Sovereign Swarm Orchestration**
> *Updated: Spring 2026 · Package metadata in tree: `v10.0.0`*
> *Classification: Planning snapshot. This file tracks capability bands and LEGION-10k scaling logic.*
> *Release truth lives in `pyproject.toml`; historical release notes live in `docs/changelog.md`.*

---

## ✅ Foundation Lineage — Delivered (C5-REAL)

**Local-First Sovereign Trust layer.**

- [x] **Tamper-evident Memory Engine** (SQLite + WAL + 384-dim ONNX Embeddings)
- [x] **Hash-Chained Ledger** (SHA-256 blocks for facts and decisions)
- [x] **Zero-GIL Rust Dispatch** (`cortex_rs` O(1) throughput bypassing Python limitations)
- [x] **AST Sandbox** (LLM code execution integrity without `eval()`)
- [x] **Privacy Shield** (11-pattern secret detection at ingress)
- [x] **Multi-tenant Core** (`tenant_id` at all storage layers)
- [x] **RBAC Engine** (4 roles, structured API access limits)

---

## 🔥 v10.0 — LEGION-10k Scaling Logic (Current Phase)

**From local Python daemon → High-performance Multi-agent network backbone supporting 10,000+ concurrent agents.**

- [x] **ZeroCopyRingBuffer Hardening** — Lock-free MPSC memory mapping for LEGION-10k swarm dispatch.
- [x] **Distributed Event Bus** — C5-REAL telemetry streaming (WebSocket @ 20Hz) to agents.archi.
- [x] **Sovereign Magic Decorator** — `@sovereign_persist` for zero-friction agent onboarding.
- [x] **EVM Topography Mapping** — Latency-optimized node routing for Ethereum, Base, and Arbitrum.
- [x] **Redis L1 Cache** — Distributed working memory for lower TTFT latency across the swarm.

---

## 🔮 v11.0 — Vision (Sovereign Cloud)

**Managed Enterprise Platform (Industrial Noir 2026 Aesthetic).**

- [ ] **PostgreSQL/AlloyDB backend** — High-throughput pgvector integration for infinite memory scaling.
- [ ] **Admin Web Dashboard** — Industrial Noir UI for memory management and cryptographically signed audit visualization.
- [ ] **Multi-node Federation** — Distributed clusters with Gossip protocol for global swarm homeostasis.
- [ ] **Dual Compliance Mode** — EU AI Act (Art. 12) + SOC 2 reporting pipelines.
- [ ] **Zero-Knowledge Encryption** — Memories encrypted at rest on hardware keys.

---

## Pricing Strategy (Cloud Roadmap)

| Tier | Price | Target |
| :--- | :--- | :--- |
| **Self-Hosted** | Free forever | On-prem, unlimited, community support. |
| **Pro** | $29/mo | Small agent ensembles, cloud database backends. |
| **Team (LEGION)** | $99/mo | Multi-agent enterprise consensus, 99.9% SLA, full swarm analytics. |

---

*Roadmap subject to Sovereign revision by borjamoskv. Execution reality level: C5-REAL.*
