<!-- [C5-REAL] Exergy-Maximized -->
<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/marketing/social-preview.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/marketing/social-preview-light.png">
    <img src="assets/marketing/social-preview.png" alt="CORTEX Persist — Tamper-evident memory for AI agents" width="100%">
  </picture>
</div>

<h1 align="center">CORTEX-PERSIST</h1>

<p align="center">
  <strong>Tamper-evident memory and decision lineage for AI agents.</strong><br>
  <em>Cryptographic proof of what your agent knew, decided, and did — sealed in an append-only execution ledger.</em>
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/cortex-persist/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/cortex-persist?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="GitHub Stars"></a>
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="PyPI"></a>
  <a href="https://github.com/borjamoskv/cortex-persist/actions"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/cortex-persist/ci.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="CI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="Python"></a>
  <a href="https://github.com/borjamoskv/cortex-persist/actions/workflows/bench.yml"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/cortex-persist/bench.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5&label=Criterion%20Bench" alt="Criterion Bench"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="License"></a>
  <a href="docs/mcp.md"><img src="https://img.shields.io/badge/MCP-compatible-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="MCP Compatible"></a>
</p>

<p align="center">
  <a href="#why-it-exists">Why it exists</a> ·
  <a href="#what-you-get">What you get</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#compare">Compare</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#mcp">MCP</a> ·
  <a href="docs/api.md">API docs</a>
</p>

---

## Why it exists

Most agent frameworks answer: **what should the agent do next?**

CORTEX-PERSIST answers something stricter: **can you prove what the agent did, and that the proof has not been altered?**

- LangGraph gives you checkpoints. CORTEX gives you cryptographic proof those checkpoints are intact.
- Mem0 gives you semantic memory. CORTEX gives you a hash-chain ledger of memory access and mutation.
- Traditional logs give you text. CORTEX gives you verifiable execution lineage.

> If a decision changes state, affects a user, or moves money, a log is not enough. You need a proof.

---

## What you get

- Append-only execution sealing.
- Hash-chain provenance for observations and mutations.
- Deterministic replay of past execution states.
- Divergence detection across runs.
- Native MCP integration.
- Python + Rust runtime for high-throughput agent infrastructure.

---

## Quick start

```bash
pip install cortex-persist
```

```python
from cortex import CortexEngine

engine = CortexEngine()
engine.observe("user_query", "What is the capital of France?")
engine.observe("agent_response", "Paris")

proof = engine.seal()
print(proof.hash)
print(proof.verify())
```

Expected result:

- `proof.hash` returns a SHA-256 digest for the sealed execution trace.
- `proof.verify()` returns `True` when the trace has not been tampered with.

---

## How it works

CORTEX-PERSIST treats agent execution as a point in a metric space, not just a log file.

Two runs of the same agent can be:

- **Equivalent** — same equivalence class in the execution manifold.
- **Divergent** — measurable drift above threshold, triggering alert, reroute, or stabilization.

This lets you inspect questions that ordinary logs do not answer well:

| Question | LangGraph | Mem0 | CORTEX-PERSIST |
| :--- | :---: | :---: | :---: |
| Did this run diverge from the canonical run? | ❌ | ❌ | ✅ `DivergenceMap` |
| Can I replay this execution deterministically? | Partial | ❌ | ✅ `ReplayEngine` |
| Is this memory state cryptographically intact? | ❌ | ❌ | ✅ Hash-chain |
| Which branch has the lowest entropy drift? | ❌ | ❌ | ✅ `MetaArbiter` |
| O(1) tamper detection on large traces? | ❌ | ❌ | ✅ Merkle seals |
| Native MCP server? | ❌ | ❌ | ✅ |
| High-throughput Rust core? | ❌ | ❌ | ✅ Rust-FFI |

---

## Core primitives

| Primitive | Purpose |
| :--- | :--- |
| `CortexEngine` | Append-only ledger for observations and state transitions. |
| `DivergenceMap` | Measures distance between execution trajectories. |
| `ReplayEngine` | Reconstructs past execution deterministically. |
| `MetaArbiter` | Selects the canonical branch under conflict. |
| `ExecutionControl` | Emits `stabilize`, `reroute`, or `halt` signals. |
| `StateDistance` | Computes distance over execution state vectors. |
| `EntropyDrift` | Tracks divergence over time windows. |

---

## Compare

CORTEX is orthogonal to LangGraph and Mem0. It sits beneath them as a verification substrate.

| Dimension | LangGraph | Mem0 | CORTEX-PERSIST |
| :--- | :--- | :--- | :--- |
| Persistence unit | Conversation thread state | Extracted semantic facts | Execution trace + hash-chain |
| Source of truth | Last checkpoint | Relevance-ranked memories | Cryptographic Merkle ledger |
| Divergence detection | None | None | `DivergenceMap` + `EntropyDrift` |
| Deterministic replay | Partial | None | Full — CI-verified |
| Multi-run topology | None | None | Equivalence classes + fork map |
| Conflict arbitration | None | None | `MetaArbiter` |
| Execution control | Graph transitions | None | `ControlSignal`: stabilize / reroute |
| Throughput | Python-bound | Python-bound | Rust-FFI core |
| Tamper evidence | None | None | SHA-256 + Merkle seals |

[See integration guide →](docs/langgraph_integration.md)

---

## Installation

Requirements: Python 3.10+. Zero external daemons required.

```bash
pip install cortex-persist
```

Optional extras:

```bash
pip install "cortex-persist[embeddings]"
pip install "cortex-persist[knowledge]"
pip install "cortex-persist[api,mcp,daemon]"
pip install "cortex-persist[cloud]"
pip install "cortex-persist[secure]"
pip install "cortex-persist[acceleration]"
```

---

## Secure credential backend

The `[secure]` extra installs `keyring` for encrypted storage of the master encryption key in the host OS vault.

```python
from cortex.crypto.keyring import get_master_key
print(get_master_key())
```

If `keyring` is not installed, `get_master_key()` returns `None` instead of raising `ModuleNotFoundError`. Minimal installations still work.

---

## MCP

CORTEX-PERSIST exposes a native MCP server for orchestrators like Claude Desktop, Perplexity, or custom agents.

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

## Real-world examples

| Example | What it demonstrates |
| :--- | :--- |
| [Canonical Loop](examples/demo_canonical.py) | Full C5-REAL execution and tamper detection. |
| [Pricing Agent](examples/demo_pricing_agent.py) | Cryptographic audit trail for AI pricing decisions. |
| [Support Escalation](examples/demo_support_approval.py) | Proof of AI decision lineage. |
| [MCP Memory](examples/demo_mcp_memory.py) | Sealed tool calls through MCP. |
| [LangGraph Integration](examples/demo_langgraph.py) | CORTEX as a verification substrate under LangGraph. |

---

## Documentation

| Resource | Description |
| :--- | :--- |
| [SECURITY_TRUST_MODEL.md](docs/SECURITY_TRUST_MODEL.md) | Cryptographic invariants and guarantees. |
| [AGENTS.md](AGENTS.md) | Autonomous orchestration directives. |
| [ROADMAP.md](ROADMAP.md) | Deployment phases and scaling path. |
| [API Reference](docs/api.md) | SDK primitives and REST endpoints. |
| [MCP Integration](docs/mcp.md) | MCP setup and tool catalog. |
| [LangGraph Integration](docs/langgraph_integration.md) | How CORTEX sits under LangGraph. |

---

```yaml
AESTHETIC:    INDUSTRIAL NOIR 2026 (#0A0A0A / #2B3BE5)
EPISTEMOLOGY: C5-REAL — Cryptographically Verified Reality
CORE TENET:   Generative output is conjecture. Evidence is absolute.
THROUGHPUT:   ~390k Agents/Sec (Rust-FFI, GIL-free)
UPDATED:      June 2026 — Execution Manifold · MetaArbiter · MCP Native
```

> **LICENSE:** Apache-2.0 | **OPERATOR:** borjamoskv | [cortexpersist.org](https://cortexpersist.org) | [Sponsor](https://github.com/sponsors/borjamoskv)
