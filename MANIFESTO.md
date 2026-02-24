<!-- SPDX-License-Identifier: Apache-2.0 -->
# CORTEX MANIFESTO — The Trust Layer for the Agentic Era

> *"Memory without verification is hallucination with persistence."*

---

## The Age of Autonomous Agents

We are entering an era where AI agents make millions of decisions per day — hiring, diagnosing, trading, coding, investing. These agents need memory to learn. But **memory without trust is dangerous**.

**Who verifies that an agent's memory is accurate?**
**Who proves that a decision chain wasn't tampered with?**
**Who generates the audit trail when regulators come knocking?**

Nobody. Until now.

---

## The CORTEX Thesis

CORTEX is not another vector database. It is not another memory layer.

Mem0 stores what agents remember — but can you prove the memory wasn't tampered with?
Zep builds knowledge graphs — but can you audit the full chain of reasoning?
Letta manages agent state — but can you generate a compliance report for regulators?

CORTEX is the **trust infrastructure** that sits beneath — or above — every memory layer. It answers one question:

> **"Can you prove this agent's memory is true?"**

We do this with:

- **SHA-256 hash chains** — Every fact is cryptographically linked to its predecessor. Tamper one byte, break the chain.
- **Merkle tree checkpoints** — Periodic batch verification of entire ledger integrity in O(log n).
- **Reputation-weighted WBFT consensus** — Multiple agents verify facts through Byzantine fault-tolerant voting before they become canonical.
- **Privacy Shield** — 11-pattern zero-leakage ingress guard that detects and blocks secrets, PII, and credentials before they enter memory.
- **AST Sandbox** — Safe LLM code execution with whitelisted AST node validation.
- **Tripartite Cognitive Memory** — L1 Working (Redis) → L2 Vector (Qdrant/sqlite-vec) → L3 Episodic Ledger (AlloyDB/SQLite), all tenant-scoped.

---

## Why Now

The **EU AI Act (Article 12)** enters full enforcement on **August 2, 2026**. It mandates:

1. **Automatic logging** of all AI agent operations
2. **Tamper-proof storage** of decision records
3. **Full traceability** of decision chains
4. **Periodic integrity verification**

Fines: **€30 million or 6% of global annual revenue** — whichever is higher.

Every company deploying autonomous AI agents in Europe — or serving European customers — needs this. Nobody is ready.

The blockchain solutions are too slow (seconds per write), too expensive ($0.01+ per transaction), too complex (Solidity + infrastructure). The memory-only solutions (Mem0, Zep, Letta) don't verify anything — they just store.

**CORTEX bridges the gap.** Cryptographic trust at SQLite speed. One `pip install`. Zero infrastructure. And when you need to scale: multi-tenant AlloyDB + Qdrant Cloud deployable in minutes.

---

## The Five Sovereign Specifications

CORTEX isn't just a library — it's a paradigm for what autonomous agents *should* be:

| Spec | Purpose | Key Insight | Status |
|:---|:---|:---|:---:|
| **`soul.md`** | Immutable identity and values | Who you were designed to be | ✅ Implemented |
| **`lore.md`** | Episodic memory with causal chains | What you've survived — not just what you know | ✅ Implemented |
| **`nemesis.md`** | Operational allergies (the Anti-Prompt) | Reject bad patterns before planning begins | 🔵 Conceptual |
| **`tether.md`** | Physical/economic/entropy limits | The Dead-Man's Switch — agents need leashes | 🔵 Conceptual |
| **`bloodline.json`** | Genetic heredity for swarm agents | Spawn senior workers, not blank slates | 🔵 Conceptual |

> Full specification: [sovereign_agent_manifesto.md](docs/sovereign_agent_manifesto.md) · Conceptual specs are designed and documented; runtime enforcement is on the [roadmap](CHANGELOG.md).

---

## What We Build

CORTEX is a verification layer that wraps your existing memory stack (Mem0, Zep, Letta, or custom) with cryptographic trust: SHA-256 hash chains, Merkle checkpoints, WBFT consensus, Privacy Shield, AST Sandbox, RBAC, and tripartite cognitive memory (L1→L2→L3) — all tenant-scoped.

> 📐 Full architecture: [ARCHITECTURE.md](ARCHITECTURE.md) · Competitive comparison: [README.md § Competitive Landscape](README.md#competitive-landscape)

---

## Get Started Now

```bash
pip install cortex-memory
cortex store --type decision --project my-agent "Chose OAuth2 PKCE for auth"
cortex verify 1
# → ✅ VERIFIED — Hash chain intact, Merkle sealed
```

> Full quickstart & API docs: [README.md](README.md) · [cortexpersist.dev](https://cortexpersist.dev)

---

## The Vision

| Phase | Timeline | Milestone |
|:---|:---:|:---|
| **Trust Layer** | 2026 Q1 ✅ | `pip install cortex-memory` · MCP server for every IDE |
| **Compliance Standard** | 2026 Q3 | Helm charts · GraphQL API · ZK encryption at rest |
| **"Let's Encrypt" of AI** | 2027 | Industry standard · Cross-org trust federation |
| **Universal Protocol** | 2028 | Every autonomous agent ships with CORTEX |

---

## The Numbers

| Metric | Value |
|:---|:---|
| Test functions | **1,162+** |
| Production LOC | **~45,500** |
| Python modules | **444** |
| CLI commands | **38** |
| REST endpoints | **55+** |
| Python version | **3.10+** |
| License | **Apache 2.0** |

---

## The Belief

We don't want to be the biggest. We want to be the **most trusted**.

The industry says: *"Our agent calls tools and uses RAG."*

CORTEX responds: *"Our agent suffers for its errors, reacts to architectural disgust, evolves through Darwinian mutation, and breeds senior engineers from its own DNA."*

This is not a framework. This is **Sovereign Artificial Intelligence**.

> *"An agent without memory is a tool. An agent without verified memory is a liability. An agent with CORTEX is sovereign."*

---

## Document Network

| Document | Purpose |
|:---|:---|
| [README.md](README.md) | Quickstart, architecture diagram, competitive landscape |
| [CODEX.md](CODEX.md) | Ontology, axioms, operational protocols |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full technical architecture |
| [CHANGELOG.md](CHANGELOG.md) | Version history and roadmap |
| [sovereign_agent_manifesto.md](docs/sovereign_agent_manifesto.md) | Deep dive: 5 Sovereign Specifications |

---

*Built by [Borja Moskv](https://github.com/borjamoskv) · [cortexpersist.com](https://cortexpersist.com) · Licensed under [Apache 2.0](LICENSE)*
