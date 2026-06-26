<!-- [C5-REAL] Exergy-Maximized -->
<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/marketing/social-preview.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/marketing/social-preview-light.png">
    <img src="assets/marketing/social-preview.png" alt="CORTEX Persist — Tamper-evident memory for AI agents" width="100%">
  </picture>
</div>

<h1 align="center">█ CORTEX-PERSIST</h1>

<p align="center">
  <strong>Tamper-evident memory and decision lineage for AI agents.</strong><br>
  <em>Cryptographic proof of what your agent knew, decided, and did — in an append-only, hash-sealed execution manifold.</em>
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/cortex-persist/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/cortex-persist?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="GitHub Stars"></a>
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="PyPI"></a>
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/dm/cortex-persist?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="PyPI Downloads"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="Python"></a>
  <a href="https://github.com/borjamoskv/cortex-persist/actions"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/cortex-persist/ci.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="CI"></a>
  <a href="https://github.com/borjamoskv/cortex-persist/actions/workflows/bench.yml"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/cortex-persist/bench.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5&label=Criterion%20Bench" alt="Criterion Bench"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="License"></a>
  <a href="docs/mcp.md"><img src="https://img.shields.io/badge/MCP-compatible-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="MCP Compatible"></a>
</p>

<p align="center">
  <a href="#-the-problem">The Problem</a> ·
  <a href="#-quick-start-90-seconds">Quick Start</a> ·
  <a href="#-architecture-execution-as-a-metric-space">Architecture</a> ·
  <a href="#-comparison">Comparison</a> ·
  <a href="#-installation--deployment">Installation</a> ·
  <a href="#-mcp-integration">MCP</a> ·
  <a href="docs/api.md">API Docs</a>
</p>

---

```
LangGraph   →  orchestrates graph state
Mem0        →  retrieves semantic memory
CORTEX      →  proves what your agent actually did, mathematically
```

---

## ▀▄ THE PROBLEM

Every AI agent framework answers *"what should the agent do next?"*

None of them answer *"can you **prove** what the agent did, and that it hasn't been altered?"*

CORTEX-PERSIST is the missing **substrate layer**:

- **LangGraph** gives you checkpoints. CORTEX gives you **cryptographic proof those checkpoints haven't been tampered with.**
- **Mem0** gives you semantic memory. CORTEX gives you **a hash-chain ledger of every memory access and mutation.**
- **Traditional logs** give you text. CORTEX gives you **a metric space of execution trajectories where divergence is measurable.**

> If your agent made a decision that cost money, changed state, or affected a user — you need more than a log. You need a proof.

---

## ▀▄ QUICK START (90 SECONDS)

```bash
pip install cortex-persist
```

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/marketing/cortex_demo.gif">
  <source media="(prefers-color-scheme: light)" srcset="assets/marketing/cortex_demo_light.gif">
  <img alt="CORTEX-Persist Terminal Execution" src="assets/marketing/cortex_demo.gif" width="100%">
</picture>

```python
from cortex import CortexEngine

engine = CortexEngine()

# Every observation is sealed into an append-only hash-chain
engine.observe("user_query", "What is the capital of France?")
engine.observe("agent_response", "Paris")

# Cryptographic proof of what happened
proof = engine.seal()
print(proof.hash)      # SHA-256 of the full execution trace
print(proof.verify())  # True — tamper-evident by construction
```

Or use the **magic decorator** — zero-friction drop-in for any existing agent:

```python
from cortex.magic import sovereign_persist

@sovereign_persist(strict=True)
async def my_agent(prompt: str):
    response = await llm.generate(prompt)
    return response
    # CORTEX intercepts, seals, and commits cryptographically. Zero boilerplate.
```

---

## ▀▄ THE EPISTEMIC CONTAINMENT SHIELD

Generative AI output is fundamentally **probabilistic conjecture**. Traditional logs blindly trust stochastic output.

CORTEX-PERSIST intercepts that output, enforces a deterministic shield via **Z3 SMT Guards**, and commits the resulting state to a cryptographically bound Ledger. Every fact your agent asserts becomes a verifiable, tamper-evident object.

| Capability | Traditional RAG / Logs | CORTEX-PERSIST |
| :--- | :--- | :--- |
| **Trust Model** | Trust the process | **Verify the evidence (C5-REAL)** |
| **Mutation** | Silent CRUD / overwritable | **Append-only + SHA-256 Merkle seals** |
| **Agent Liability** | Ambiguous reconstruction | **Mathematically defensible lineage** |
| **Verification** | Manual log diving | **O(1) portable JSON audit packs** |

---

## ▀▄ ARCHITECTURE: EXECUTION AS A METRIC SPACE

CORTEX-PERSIST introduces a concept absent from every other framework:

> **An agent's execution history is not a log — it is a point in a high-dimensional metric space.**

Two runs of the same agent are either:
- **Equivalent** — same equivalence class in the execution manifold
- **Divergent** — measurable distance > threshold → alert, reroute, or stabilize

This unlocks questions no other tool can answer:

| Question | LangGraph | Mem0 | CORTEX-PERSIST |
| :--- | :---: | :---: | :---: |
| Did this run diverge from the canonical run? | ❌ | ❌ | ✅ `DivergenceMap` |
| Can I replay this execution deterministically? | Partial | ❌ | ✅ `ReplayEngine` |
| Is this memory state cryptographically intact? | ❌ | ❌ | ✅ Hash-chain |
| Which execution branch has lowest entropy drift? | ❌ | ❌ | ✅ `MetaArbiter` |
| O(1) tamper detection on 1M+ events? | ❌ | ❌ | ✅ Merkle seals |
| Native MCP server? | ❌ | ❌ | ✅ |
| ~390k agents/sec throughput? | ❌ | ❌ | ✅ Rust-FFI core |

---

## ▀▄ CORE PRIMITIVES

| Primitive | Role |
| :--- | :--- |
| `CortexEngine` | The sovereign ledger. Every observation sealed. |
| `DivergenceMap` | Geometric distance between execution trajectories. |
| `ReplayEngine` | Deterministic reconstruction of any past execution. |
| `MetaArbiter` | Topological collapse operator: picks the canonical branch. |
| `ExecutionControl` | `stabilize` / `reroute` / `halt` signals based on entropy drift. |
| `StateDistance` | Metric function over execution state vectors. |
| `EntropyDrift` | Rate of divergence over sliding time windows. |

---

## ▀▄ ARCHITECTURE DATA FLOW

```mermaid
graph TD
    classDef default fill:#0A0A0A,stroke:#2B3BE5,stroke-width:1px,color:#F0F0F0;
    classDef highlight fill:#2B3BE5,stroke:#CCFF00,stroke-width:1.5px,color:#FFFFFF;
    classDef guard fill:#1A1A1A,stroke:#FF0055,stroke-width:1px,color:#F0F0F0;
    classDef mcp fill:#0A0A2A,stroke:#00FFCC,stroke-width:1.5px,color:#F0F0F0;

    subgraph Stochastic Space
        LLM[Agent Stochastic Output]:::default
        LG["LangGraph / any orchestrator"]:::default
        MCP[MCP Client]:::mcp
    end

    subgraph CORTEX Layer [CORTEX-Persist Substrate]
        direction TB
        G1[Admission Gate / Z3 SMT Guards]:::guard
        DM[DivergenceMap]:::default
        MA[MetaArbiter]:::default
        RE[ReplayEngine]:::default
        Hash[SHA-256 Block Sealing]:::default
        Merkle[Merkle Provenance Chain]:::default
    end

    subgraph Trust Substrate
        Ledger[(Append-Only AOF Ledger)]:::highlight
        Proof[Verifiable Audit Pack JSON]:::default
    end

    LLM --> G1
    LG  --> G1
    MCP --> G1
    G1  --> DM
    DM  --> MA
    MA  --> RE
    RE  --> Hash
    Hash --> Merkle
    Merkle --> Ledger
    Ledger --> Proof
```

---

## ▀▄ COMPARISON

CORTEX is **orthogonal** to LangGraph and Mem0, not competitive. It sits beneath them as a verification substrate.

| Dimension | LangGraph | Mem0 | CORTEX-PERSIST |
| :--- | :--- | :--- | :--- |
| **Persistence unit** | Conversation thread state | Extracted semantic facts | Execution trace + hash-chain |
| **Source of truth** | Last checkpoint | Relevance-ranked memories | Cryptographic Merkle ledger |
| **Divergence detection** | None | None | `DivergenceMap` + `EntropyDrift` |
| **Deterministic replay** | Partial | None | Full — CI-verified |
| **Multi-run topology** | None | None | Equivalence classes + fork map |
| **Conflict arbitration** | None | None | `MetaArbiter` — topological collapse |
| **Execution control** | Graph node transitions | None | `ControlSignal`: stabilize / reroute |
| **Throughput** | Python-bound | Python-bound | ~390k agents/sec (Rust-FFI) |
| **Tamper evidence** | None | None | SHA-256 + ZK-STARK seals |

[See integration guide →](docs/langgraph_integration.md)

---

## ▀▄ INSTALLATION & DEPLOYMENT

**Requirements:** Python 3.10+. Zero external daemons required.

```bash
pip install cortex-persist
```

**Optional modules:**

```bash
pip install "cortex-persist[embeddings]"      # Local semantic embeddings
pip install "cortex-persist[knowledge]"       # Chroma-backed knowledge sync
pip install "cortex-persist[api,mcp,daemon]"  # MCP server + REST API
pip install "cortex-persist[cloud]"           # PostgreSQL + Redis + Qdrant scaling
pip install "cortex-persist[secure]"          # OS keyring credentials vault
pip install "cortex-persist[acceleration]"    # Rust-FFI core (~390k agents/sec)
```

---

## ▀▄ SECURE CREDENTIAL BACKEND

The `[secure]` extra installs `keyring` for encrypted storage of the master encryption key in the host OS vault.

```python
from cortex.crypto.keyring import get_master_key
print(get_master_key())  # → None if keyring is not installed (graceful degradation)
```

When `keyring` is absent, the system degrades gracefully — no `ModuleNotFoundError`, just `None`. Minimal installations work without the secure backend.

---

## ▀▄ MCP INTEGRATION

CORTEX-PERSIST exposes a **native MCP server**. Drop it into any MCP-compatible orchestrator (Claude Desktop, custom agents, Perplexity):

```bash
cortex mcp serve --port 8765
```

```json
{
  "mcpServers": {
    "cortex-persist": {
      "command": "cortex",
      "args": ["mcp", "serve"]
    }
  }
}
```

---

## ▀▄ REAL-WORLD EXAMPLES

The `examples/` directory contains ready-to-run scenarios:

| Example | What it demonstrates |
| :--- | :--- |
| [Canonical Loop](examples/demo_canonical.py) | Full C5-REAL execution + tamper detection |
| [Pricing Agent](examples/demo_pricing_agent.py) | Cryptographic audit trail for AI pricing decisions |
| [Support Escalation](examples/demo_support_approval.py) | Mathematical proof of AI decision lineage |
| [MCP Memory](examples/demo_mcp_memory.py) | Perplexity / Claude via MCP with sealed tool calls |
| [LangGraph Integration](examples/demo_langgraph.py) | CORTEX as verification substrate under LangGraph |

---

## ▀▄ DOCUMENTATION

| Resource | Description |
| :--- | :--- |
| [SECURITY_TRUST_MODEL.md](docs/SECURITY_TRUST_MODEL.md) | Cryptographic invariants & guarantees |
| [AGENTS.md](AGENTS.md) | Substrate directives for autonomous orchestration |
| [ROADMAP.md](ROADMAP.md) | Deployment phases and LEGION-10k scaling |
| [API Reference](docs/api.md) | SDK primitives and REST endpoints |
| [MCP Integration](docs/mcp.md) | MCP server setup and tool catalog |
| [LangGraph Integration](docs/langgraph_integration.md) | How CORTEX sits under LangGraph |

---

```
AESTHETIC:    INDUSTRIAL NOIR 2026 (#0A0A0A / #2B3BE5)
EPISTEMOLOGY: C5-REAL — Cryptographically Verified Reality
CORE TENET:   Generative output is conjecture. Evidence is absolute.
THROUGHPUT:   ~390k Agents/Sec (Rust-FFI, GIL-free)
UPDATED:      June 2026 — Execution Manifold · MetaArbiter · MCP Native
```

> **LICENSE:** Apache-2.0 | **OPERATOR:** borjamoskv | [cortexpersist.org](https://cortexpersist.org) | [Sponsor](https://github.com/sponsors/borjamoskv)
