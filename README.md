🌐 **English** | [Español](README.es.md) | [中文](README.zh.md)

# CORTEX — Trust Infrastructure for Autonomous AI

> **Your AI agent makes thousands of decisions. Can you prove a single one wasn't tampered with?**
> *CORTEX is to AI memory what SSL/TLS is to web communications — cryptographic verification, audit trails, and EU AI Act compliance out of the box.*

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Status](https://img.shields.io/badge/status-v7.0%20alpha-orange.svg)
![CI](https://github.com/borjamoskv/cortex/actions/workflows/ci.yml/badge.svg)
[![Coverage](https://codecov.io/gh/borjamoskv/cortex/branch/master/graph/badge.svg)](https://codecov.io/gh/borjamoskv/cortex)
![Signed](https://img.shields.io/badge/releases-sigstore%20signed-2FAF64.svg)
![Security](https://img.shields.io/badge/scan-trivy%20%2B%20pip--audit-blue.svg)
[![Docs](https://img.shields.io/badge/docs-cortexpersist.dev-brightgreen)](https://cortexpersist.dev)
[![Website](https://img.shields.io/badge/web-cortexpersist.com-blue)](https://cortexpersist.com)
[![Cross-Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-blue)](docs/cross_platform_guide.md)

### ⚡ The Numbers

| | |
|:---|:---|
| **<20ms** retrieval | In-process SQLite. No HTTP. No network. |
| **$258K/yr** saved | Context-reconstruction debt eliminated for a 10-dev team |
| **1,162+** tests | Production-grade from day one |
| **Zero** attack surface | No HTTP endpoints. No cloud dependency. No CVSS 9.1. |

---

## The Problem

AI agents are making millions of decisions per day. **Nobody can prove those decisions are correct.**

- **Mem0** stores memories — with [CVSS 9.1 vulnerabilities](https://github.com/mem0ai/mem0/issues) open in production (SSRF, arbitrary file read). Can you trust it with enterprise data?
- **Zep** builds knowledge graphs. Can you audit the full chain of reasoning? Generate a compliance report?
- **Letta** manages agent state. But nothing is hash-chained, nothing is tamper-proof.

Meanwhile, the **EU AI Act (Article 12, enforcement: August 2026)** demands:

- ✅ Automatic logging of all agent decisions
- ✅ **Tamper-proof** storage of decision records
- ✅ Full traceability and explainability
- ✅ Periodic integrity verification

**Fines: up to €30M or 6% of global revenue.** The clock is ticking.

## What CORTEX Makes Impossible

> *The most valuable guarantee of a system is not what it does — it's what it makes architecturally unreachable.*

| Failure | Without CORTEX | Guarantee |
|:--------|:--------------|:---------:|
| **Session Amnesia** | Every session is T₀. Months of decisions vanish. Agents reconstruct from hallucination. | `STRUCTURAL` |
| **Repeated Errors** | Same architectural mistake, re-diagnosed from scratch. Learning curve resets per conversation. | `BEHAVIORAL` |
| **Fabricated History** | LLM invents coherent rationale for decisions never made. Indistinguishable from truth. | `CRYPTOGRAPHIC` |
| **Ghost Accumulation** | Incomplete work is invisible. Work restarts silently from scratch. Infinite waste loop. | `STRUCTURAL` |
| **Multi-Agent Divergence** | Two agents build different realities. Silent conflict until production. | `CONSENSUS` |

**CORTEX doesn't test whether your agent behaves like it remembers. It makes not-remembering structurally impossible.**

→ Full technical reference: [docs/impossible-failures.md](docs/impossible-failures.md)

---

## The Solution

CORTEX doesn't replace your memory layer — it **certifies** it.

```
Your Memory Layer (Mem0 / Zep / Letta / Custom)
        ↓
   CORTEX Trust Engine v7
        ├── 🧬 Biological Core (Autopoiesis/Endocrine)
        ├── 🛡️ Zero-Trust Guards (Connection/Storage)
        ├── 🚀 SHIPPER-Ω (Automated Deployment Orchestration)
        ├── 🔗 SHA-256 hash-chained ledger
        ├── Merkle tree checkpoints
        ├── Reputation-weighted WBFT consensus
        ├── Privacy Shield (11-pattern secret detection)
        ├── AST Sandbox (safe LLM code execution)
        └── EU AI Act compliance reports
```

### Core Capabilities

| Capability | What It Does | EU AI Act |
|:---|:---|:---:|
| 🔗 **Immutable Ledger** | Every fact is SHA-256 hash-chained. Tamper = detectable. | Art. 12.3 |
| 🌳 **Merkle Checkpoints** | Periodic batch verification of ledger integrity | Art. 12.4 |
| 📋 **Audit Trail** | Timestamped, hash-verified log of all decisions | Art. 12.1 |
| 🔍 **Decision Lineage** | Trace how an agent arrived at any conclusion | Art. 12.2d |
| 🤝 **WBFT Consensus** | Multi-agent Byzantine fault-tolerant verification | Art. 14 |
| 📊 **Compliance Report** | One-command regulatory readiness snapshot | Art. 12 |
| 🧠 **Tripartite Memory** | L1 Working → L2 Vector → L3 Episodic Ledger | — |
| 🧬 **Biological Core** | Autopoiesis + Endocrine + Circadian Cycles | — |
| 🔐 **Privacy Shield** | Zero-leakage ingress guard — 11 secret patterns | — |
| 🏠 **Local-First** | SQLite. No cloud required. Your data, your machine. | — |
| ☁️ **Sovereign Cloud** | Multi-tenant AlloyDB + Qdrant + Redis (v6) | — |

---

## Quick Start

### Install

```bash
pip install cortex-memory
```

### Store a Decision & Verify It

```bash
# Store a fact (auto-detects AI agent source)
cortex store --type decision --project my-agent "Chose OAuth2 PKCE for auth"

# Verify its cryptographic integrity
cortex verify 42
# → ✅ VERIFIED — Hash chain intact, Merkle sealed

# Generate compliance report
cortex compliance-report
# → Compliance Score: 5/5 — All Article 12 requirements met
```

### Multi-Tenant (v8)

```python
from cortex import CortexEngine

engine = CortexEngine()

# All operations are now tenant-scoped
await engine.store_fact(
    content="Approved loan application #443",
    fact_type="decision",
    project="fintech-agent",
    tenant_id="enterprise-customer-a"
)
```

### Run as MCP Server (Universal IDE Plugin)

```bash
# Works with: Claude Code, Cursor, OpenClaw, Windsurf, Antigravity
python -m cortex.mcp
```

### Run as REST API

```bash
uvicorn cortex.api:app --port 8484
```

---

## Architecture (v8 — Sovereign Cloud)

```mermaid
block-beta
  columns 1

  block:INTERFACES["🖥️ INTERFACES"]
    CLI["CLI (38 cmds)"]
    API["REST API (55+ endpoints)"]
    MCP["MCP Server"]
    GraphQL["GraphQL (soon)"]
  end

  block:GATEWAY["🔐 TRUST GATEWAY"]
    RBAC["RBAC (4 roles)"]
    Privacy["Privacy Shield"]
    Auth["API Keys + JWT"]
    Security["Security Middleware"]
  end

  block:MEMORY["🧠 COGNITIVE MEMORY"]
    L1["L1: Redis / Working Memory"]
    L2["L2: Qdrant / sqlite-vec (384-dim)"]
    L3["L3: AlloyDB / SQLite (hash-chained)"]
    Bio["🧬 Biological: Autopoietic Core"]
  end

  block:TRUST["⛓️ TRUST LAYER"]
    Ledger["SHA-256 Ledger"]
    Merkle["Merkle Trees"]
    WBFT["WBFT Consensus"]
    Sandbox["AST Sandbox"]
  end

  block:PLATFORM["⚙️ PLATFORM SERVICES"]
    Daemon["Self-Healing Daemon"]
    Notifications["Notification Bus"]
    Compaction["Compaction Sidecar"]
    EdgeSync["EdgeSyncMonitor"]
  end

  INTERFACES --> GATEWAY --> MEMORY --> TRUST --> PLATFORM
```

> 📐 Full architecture details in [ARCHITECTURE.md](ARCHITECTURE.md) and [docs](https://cortexpersist.dev/architecture/).

---

## Competitive Landscape

| | **CORTEX** | Mem0 | Zep | Letta | RecordsKeeper |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Cryptographic Ledger** | ✅ | ❌ | ❌ | ❌ | ✅ (blockchain) |
| **Merkle Checkpoints** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Multi-Agent Consensus** | ✅ WBFT | ❌ | ❌ | ❌ | ❌ |
| **Privacy Shield** | ✅ 11 patterns | ❌ | ❌ | ❌ | ❌ |
| **AST Sandbox** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Local-First** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **No Blockchain Overhead** | ✅ | — | — | — | ❌ |
| **MCP Native** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Multi-Tenant (v6)** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **EU AI Act Ready** | ✅ | ❌ | ❌ | ❌ | Partial |
| **Cost** | **Free (Apache 2.0)** | $249/mo | $$$ | Free | $$$ |
| **SSRF Vulnerabilities** | **None** | CVSS 9.1 (Feb 2026) | — | — | — |

---

## Stats (2026-02-24)

| Metric | Value |
|:---|:---|
| Test functions | **1,162+** |
| Production LOC | **~45,500** |
| Python Modules | **444** |
| Python version | **3.10+** |

---

## Integrations

CORTEX plugs into your existing stack:

- **IDEs**: Claude Code, Cursor, OpenClaw, Windsurf, Antigravity (via MCP)
- **Agent Frameworks**: LangChain, CrewAI, AutoGen, Google ADK
- **Memory Layers**: Sits on top of Mem0, Zep, Letta as verification layer
- **Databases**: SQLite (local), AlloyDB, PostgreSQL, Turso (edge)
- **Vector Stores**: sqlite-vec (local), Qdrant (self-hosted or cloud)
- **Deployment**: Docker, Kubernetes (Helm coming Q2 2026), bare metal, `pip install`

---

## Cross-Platform

CORTEX runs natively on any environment without Docker:

- **macOS** (launchd & osascript notifications)
- **Linux** (systemd & notify-send)
- **Windows** (Task Scheduler & PowerShell)

See [Cross-Platform Architecture Guide](docs/cross_platform_guide.md).

---

## Why CORTEX? Why Now?

1. **EU AI Act enforcement: August 2026.** Companies without audit trails face €30M fines.
2. **Competitor vulnerabilities are public.** Mem0 SSRF (CVSS 9.1) remains open.
3. **Context-reconstruction costs compound daily.** 45 min/dev/day × 230 days = $258K/yr for 10 engineers.
4. **Local-first is non-negotiable** for defense, healthcare, banking, and legal.
5. **CORTEX is free.** Apache 2.0. Zero risk to evaluate. 30 seconds to install.

---

## License

**Apache License 2.0** — Free for any use, commercial or non-commercial.
See [LICENSE](LICENSE) for details.

---

*Built by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
