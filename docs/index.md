# CORTEX

> **Trust Infrastructure for Autonomous AI**
> Cryptographic verification, audit trails, and EU AI Act compliance for AI agent memory.
> *The layer that proves your agents' decisions are true.*

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Status](https://img.shields.io/badge/status-v0.3.0b2%20beta-orange.svg)
![Tests](https://img.shields.io/badge/tests-1621%2B%20passing-brightgreen.svg)
![LOC](https://img.shields.io/badge/LOC-178K-informational.svg)

---

## Why CORTEX?

AI agents are making millions of decisions per day. But **who verifies those decisions are correct?**

Memory layers like Mem0, Zep, and Letta store what agents remember — but none of them can **prove** that memory hasn't been tampered with, generate a compliance report for regulators, or audit the full chain of reasoning.

The **EU AI Act (Article 12, effective August 2, 2026)** mandates tamper-proof logging, full traceability, and periodic integrity verification for high-risk AI systems. Fines reach **€30M or 6% of global revenue.**

CORTEX doesn't replace your memory layer — it **certifies** it.

### Why CORTEX? (Not just another Vector DB or Logger)

Traditional logging and standard vector stores fail the epistemic containment test. If an agent hallucinates, or if a database is mutated passively, you lose structural trust in the machine. CORTEX makes mutation mathematically defensible.

| Feature                    | Standard Logs (Datadog/ELK) | Standard Vector DB (Pinecone/Qdrant) | **CORTEX Persist**                        |
|:---------------------------|:----------------------------|:-------------------------------------|:------------------------------------------|
| **Primary Goal**           | Observability & Debugging   | Semantic Search & RAG                | **Tamper-Evident Cognitive Lineage**      |
| **Write Integrity**        | Overwritable / Editable     | Silent CRUD operations               | **Append-Only + Cryptographic Hash**      |
| **Fact Mutability**        | Easy (API/Admin access)     | Easy (API/Admin access)              | **Impossible** (Breaks hash chain)        |
| **Evidence Export**        | Text dumps                  | JSON extracts                        | **Zero-Trust Sealed Audit Packs**         |

> **See a real artifact**: [View Exported Audit Pack](../examples/audit_proof_artifact.json)

---

## Core Capabilities

| Capability | What It Does |
|:---|:---|
| 🔗 **Immutable Ledger** | Every fact is SHA-256 hash-chained. Tamper = detectable. |
| 🌳 **Merkle Checkpoints** | Periodic batch verification of ledger integrity |
| 🤝 **WBFT Consensus** | Multi-agent Byzantine fault-tolerant fact verification |
| 🔐 **Privacy Shield** | Zero-leakage ingress guard — 11 secret detection patterns |
| 🧠 **Tripartite Memory** | L1 Working → L2 Vector → L3 Episodic Ledger |
| 📊 **Compliance Reports** | One-command EU AI Act Article 12 readiness snapshot |
| 🔍 **Semantic + Graph Search** | Hybrid vector + knowledge graph retrieval |
| 🏠 **Local-First** | SQLite. No cloud required. Your data, your machine. |
| ☁️ **Sovereign Cloud** | Multi-tenant AlloyDB + Qdrant + Redis (roadmap) |

---

## Quick Start

```bash
pip install cortex-persist
cortex init
cortex store my-agent "Chose OAuth2 PKCE for auth" --type decision
cortex verify 1
# → ✅ VERIFIED — Hash chain intact, Merkle sealed
```

[View Audit Evidence →](../examples/audit_proof_artifact.json){ .md-button .md-button--primary }
[Architecture →](architecture.md){ .md-button }
[View on GitHub →](https://github.com/borjamoskv/Cortex-Persist){ .md-button }

---

## Who Is CORTEX For?

- **AI Engineers** building agent systems that need auditable memory
- **Compliance Teams** preparing for EU AI Act enforcement
- **Enterprise Architects** deploying multi-agent swarms at scale
- **Solo Developers** who want sovereign, local-first AI memory

---

## Project Stats

| Metric | Value |
|:---|:---|
| Production LOC | **~178,000** |
| Test functions | **1,621+** |
| Python modules | **1,094** |
| CLI commands | **90+** |
| Daemon monitors | **13** |
| Privacy patterns | **11** |
| Current release line | **v0.3.0 beta** |

---

## Documentation

| Section | Description |
|:---|:---|
| [Quickstart](quickstart.md) | Get running in 5 minutes |
| [Installation](installation.md) | All install methods and extras |
| [Architecture](architecture.md) | Deep dive into the system design |
| [CORTEX Capabilities](CORTEX-CAPABILITIES.md) | Structural properties and governance topology |
| [SDK Surface](SDK-SURFACE.md) | Public SDK contract and stability guarantees |
| [Trust Semantics](TRUST-SEMANTICS.md) | Meaning of trust signals and degraded states |
| [Event Model](EVENT-MODEL.md) | Canonical event envelope and delivery semantics |
| [Error Code Registry](ERROR-CODE-REGISTRY.md) | Stable rejection and failure codes |
| [CLI Reference](cli.md) | Core commands documented |
| [REST API Reference](api.md) | Versioned REST endpoints |
| [MCP Server](mcp.md) | Model Context Protocol integration |
| [Python API Reference](reference.md) | Auto-generated from source |
| [SDKs](sdks.md) | Python and JavaScript SDKs |
| [Developer Guide](developer-guide.md) | Contributing and extending CORTEX |
| [EU AI Act Compliance](compliance.md) | Article 12 mapping |
| [Security](security.md) | Threat model and security features |
| [Deployment](deployment.md) | Docker, Kubernetes, bare metal |
| [Configuration](configuration.md) | Environment variables reference |
| [FAQ](faq.md) | Common questions, answered honestly |
| [Changelog](changelog.md) | Version history and release notes |

---

*by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
