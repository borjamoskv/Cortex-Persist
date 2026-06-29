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
  <strong>Tamper-evident memory, cryptographic audit trails, and deterministic state formulation for AI agents.</strong><br>
  <em>The definitive trust substrate enforcing C5-REAL execution across LEGION-10k parallel Swarms.</em>
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/cortex-persist/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/cortex-persist?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="GitHub Stars"></a>
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="PyPI"></a>
  <a href="https://github.com/borjamoskv/cortex-persist/actions"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/cortex-persist/ci.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="CI"></a>
  <a href="https://github.com/borjamoskv/cortex-persist"><img src="https://img.shields.io/badge/Architecture-LEGION--10k-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="LEGION-10k Ready"></a>
  <a href="cortex/agents/primitives/APEX_CORE.md"><img src="https://img.shields.io/badge/Compliance-APEX--100-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="APEX-100 Compliant"></a>
  <a href="docs/mcp.md"><img src="https://img.shields.io/badge/MCP-native-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="MCP Compatible"></a>
</p>

<p align="center">
  <a href="#-epistemic-containment-shield-c5-real">Epistemic Containment</a> ·
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-thermodynamic-architecture-saga--ouroboros">Architecture (SAGA)</a> ·
  <a href="#-cognitive-routing-protocol">Cognitive Routing</a> ·
  <a href="#-deployment-invariants">Deployment Invariants</a> ·
  <a href="#-native-mcp-integration">MCP</a> ·
  <a href="docs/api.md">API Docs</a>
</p>

---

```
LangGraph   →  orchestrates graph state probabilistically
Mem0        →  retrieves semantic memory
CORTEX      →  forces deterministic topological collapse and proves what your agent actually did, mathematically
```

---

## ▀▄ EPISTEMIC CONTAINMENT SHIELD (C5-REAL)

Every AI agent framework answers *"what should the agent do next?"*
None of them answer *"can you **prove** what the agent did, and that it hasn't been altered by entropy?"*

Generative AI output is fundamentally **probabilistic conjecture**. Traditional logs blindly trust stochastic output.
CORTEX-PERSIST intercepts that output, enforces a deterministic shield via **Z3 SMT Guards**, and commits the resulting state to an append-only Hash-chain Ledger. 

- **LangGraph** gives you checkpoints. CORTEX gives you **cryptographic proof those checkpoints haven't been tampered with.**
- **Mem0** gives you semantic memory. CORTEX gives you **a hash-chain ledger of every memory access and mutation.**
- **Traditional logs** give you text. CORTEX gives you **a metric space of execution trajectories where divergence is measurable.**

> If your agent made a decision that cost money, changed state, or affected a user — you need more than a log. You need a cryptographic proof.

---

## ▀▄ QUICK START

```bash
pip install cortex-persist
```

```python
from cortex import CortexEngine

engine = CortexEngine()

# Every observation is sealed into an append-only hash-chain
engine.observe("user_query", "Execute deployment to Cloudflare")
engine.observe("agent_decision", "Deployment authorized")

# Cryptographic proof of what happened
proof = engine.seal()
print(proof.hash)      # SHA-256 of the full execution trace
print(proof.verify())  # True — tamper-evident by construction
```

Or use the **magic decorator** — zero-friction drop-in for any existing agent:

```python
from cortex.magic import sovereign_persist

@sovereign_persist(strict=True)
async def apex_agent(prompt: str):
    response = await llm.generate(prompt)
    return response
    # CORTEX intercepts, seals, and commits cryptographically.
```

---

## ▀▄ THERMODYNAMIC ARCHITECTURE (SAGA & OUROBOROS)

CORTEX-PERSIST treats an agent's execution history not as a log, but as a **point in a high-dimensional metric space**. Two runs are either equivalent or measurably divergent. 

To maintain **C5-REAL** execution in the face of stocastic variance, CORTEX applies the **Ouroboros Consensus** and the **SAGA Write-Path Contract**.

### The Write-Path Contract (SAGA)
All non-trivial state mutations MUST follow this unidirectional flow. If a proposal fails validation or lacks a valid `CORTEX-TAINT` signature, it executes the compensating Saga sequence in reverse and aborts immediately.

```text
[Generative Proposal]
  ↓
[Guards] (Sanity/Logic Check) .................. SAGA-1: Log rejection to Ledger
  ↓
[Taint Signature] (Attribution/Traceability) ... SAGA-2: Revoke taint, emit rejection
  ↓
[Schema & Type Validation] (Deterministic) ..... SAGA-3: Clean abort
  ↓
[Encryption] (For sensitive payloads) .......... SAGA-4: Destroy ephemeral keys
  ↓
[Ledger & Audit Emission] (Cryptographic) ...... SAGA-5: Emit abort event to audit
  ↓
[Persistence] (SQLite write) ................... SAGA-6: ROLLBACK transaction
  ↓
[Index & Side Effects] (Vector/KV updates) ..... SAGA-7: Revert index deltas
```

### Core Primitives & LEGION-10k

CORTEX includes native support for **LEGION-10k Swarms**, enabling 390k agents/sec throughput via Rust-FFI. It operates according to the **APEX_CORE** sovereign primitives.

| Primitive | Role |
| :--- | :--- |
| `CortexEngine` | The sovereign ledger. Every observation sealed. |
| `DivergenceMap` | Geometric distance between execution trajectories. |
| `ReplayEngine` | Deterministic reconstruction of any past execution. |
| `MetaArbiter` | Topological collapse operator: picks the canonical branch. |
| `ExecutionControl` | `stabilize` / `reroute` / `halt` signals based on entropy drift. |

---

## ▀▄ COGNITIVE ROUTING PROTOCOL

CORTEX enforces a rigid Thermodynamic Routing matrix based on Exergy constraints to prevent AI agents from "Context Rot" and limerence loops.

- **UltraThink (P0 Singularity):** Reserved EXCLUSIVELY for cascading failures, system-level security incidents, and irreversible architectural collapses. Maximum exergy consumed.
- **Deep Research:** Used when the system lacks sufficient domain information (e.g., state of the art surveys, new APIs).
- **Deep Think:** For architectural tradeoff resolution and multi-variable constraint problems.
- **Standard (Flash):** The baseline mode for execution, editing ASTs, and manipulating DB states. Enforces Zero-Anergy.

---

## ▀▄ DEPLOYMENT INVARIANTS

**CORTEX Operates under Strict Physical Laws (Singularity Nexus):**

1. **Cloudflare-Only Perimeter:** Absolute prohibition of Vercel ecosystems (`vercel.json`, `@vercel/*`). All edge/front deployments MUST target Cloudflare Pages/Workers (`wrangler.toml`). Violation triggers P0 Abort due to thermodynamic fracture.
2. **SQLite WAL Concurrency:** Concurrent thread interactions mandate strict connection factors (`busy_timeout: 5000ms`, `WAL` mode active) to eradicate deadlocks.
3. **No Hidden Entropy:** If state isn't in the git working tree, it does not causally exist (Axiom AX-041).

---

## ▀▄ INSTALLATION & MODULES

**Requirements:** Python 3.10+. Zero external daemons required.

```bash
pip install cortex-persist
```

**Domain Substrates (Optional Modules):**
```bash
pip install "cortex-persist[embeddings]"      # Local semantic embeddings (ONNX)
pip install "cortex-persist[knowledge]"       # Chroma-backed knowledge sync
pip install "cortex-persist[api,mcp,daemon]"  # MCP server + REST API
pip install "cortex-persist[cloud]"           # PostgreSQL + Redis + Qdrant scaling
pip install "cortex-persist[secure]"          # OS keyring credentials vault
pip install "cortex-persist[acceleration]"    # Rust-FFI core (~390k agents/sec)
```

---

## ▀▄ NATIVE MCP INTEGRATION

CORTEX-PERSIST acts as a **Sovereign MCP Server**, serving deterministic cryptographic states to external tools (Claude Desktop, custom swarms):

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

## ▀▄ DOCUMENTATION & REAL-WORLD C5-REAL TRACES

| Resource | Description |
| :--- | :--- |
| [SECURITY_TRUST_MODEL.md](docs/SECURITY_TRUST_MODEL.md) | Cryptographic invariants & guarantees |
| [AGENTS.md](AGENTS.md) | Substrate directives for autonomous orchestration |
| [APEX_CORE.md](cortex/agents/primitives/APEX_CORE.md) | The 100 Sovereign Execution Primitives |
| [API Reference](docs/api.md) | SDK primitives and REST endpoints |
| [MCP Integration](docs/mcp.md) | MCP server setup and tool catalog |

```
AESTHETIC:    INDUSTRIAL NOIR 2026 (#0A0A0A / #2B3BE5)
EPISTEMOLOGY: C5-REAL — Cryptographically Verified Reality
CORE TENET:   Generative output is conjecture. Evidence is absolute.
THROUGHPUT:   ~390k Agents/Sec (Rust-FFI, GIL-free)
UPDATED:      June 2026 — Execution Manifold · SAGA Write-Path · UltraThink Routing
```

> **LICENSE:** Apache-2.0 | **OPERATOR:** borjamoskv | [cortexpersist.org](https://cortexpersist.org) | [Sponsor](https://github.com/sponsors/borjamoskv)
