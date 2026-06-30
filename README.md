<!-- [C5-REAL] Exergy-Maximized -->
<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/marketing/social-preview.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/marketing/social-preview-light.png">
    <img src="assets/marketing/social-preview.png" alt="BABYLON-60 Persist — Tamper-evident memory for AI agents" width="100%">
  </picture>
</div>

<h1 align="center">█ BABYLON-60</h1>

<p align="center">
  <strong>Tamper-evident memory, cryptographic audit trails, and deterministic state formulation for AI agents.</strong><br>
  <em>The definitive trust substrate enforcing C5-REAL execution across LEGION-10k parallel Swarms.</em>
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/BABYLON-60/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/BABYLON-60?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="GitHub Stars"></a>
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="PyPI"></a>
  <a href="https://github.com/borjamoskv/BABYLON-60/actions"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/BABYLON-60/ci.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="CI"></a>
  <a href="https://github.com/borjamoskv/BABYLON-60"><img src="https://img.shields.io/badge/Architecture-LEGION--10k-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="LEGION-10k Ready"></a>
  <a href="cortex/agents/primitives/APEX_CORE.md"><img src="https://img.shields.io/badge/Compliance-APEX--100-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="APEX-100 Compliant"></a>
  <a href="docs/mcp.md"><img src="https://img.shields.io/badge/MCP-native-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="MCP Compatible"></a>
  <a href="FINAL_AUDIT.md"><img src="https://img.shields.io/badge/Audit-C5--REAL%202026--06--30-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="Audit C5-REAL"></a>
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

```text
LangGraph   →  orchestrates graph state probabilistically
Mem0        →  retrieves semantic memory
CORTEX      →  forces deterministic topological collapse and proves what your agent actually did, mathematically
```

---

## ▀▄ EPISTEMIC CONTAINMENT SHIELD (C5-REAL)

Every AI agent framework answers *"what should the agent do next?"*
None of them answer *"can you **prove** what the agent did, and that it hasn't been altered by entropy?"*

Generative AI output is fundamentally **probabilistic conjecture**. Traditional logs blindly trust stochastic output.
BABYLON-60 intercepts that output, enforces a deterministic shield via **Z3 SMT Guards**, and commits the resulting state to an append-only Hash-chain Ledger.

- **LangGraph** gives you checkpoints. BABYLON-60 gives you **cryptographic proof those checkpoints haven't been tampered with.**
- **Mem0** gives you semantic memory. BABYLON-60 gives you **a hash-chain ledger of every memory access and mutation.**
- **Traditional logs** give you text. BABYLON-60 gives you **a metric space of execution trajectories where divergence is measurable.**

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

BABYLON-60 treats an agent's execution history not as a log, but as a **point in a high-dimensional metric space**. Two runs are either equivalent or measurably divergent.

To maintain **C5-REAL** execution in the face of stocastic variance, BABYLON-60 applies the **Ouroboros Consensus** and the **SAGA Write-Path Contract**.

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

BABYLON-60 includes native support for **LEGION-10k Swarms**, enabling 390k agents/sec throughput via Rust-FFI. It operates according to the **APEX_CORE** sovereign primitives.

| Primitive | Role |
| :--- | :--- |
| `CortexEngine` | The sovereign ledger. Every observation sealed. |
| `DivergenceMap` | Geometric distance between execution trajectories. |
| `ReplayEngine` | Deterministic reconstruction of any past execution. |
| `MetaArbiter` | Topological collapse operator: picks the canonical branch. |
| `ExecutionControl` | `stabilize` / `reroute` / `halt` signals based on entropy drift. |

---

## ▀▄ COGNITIVE ROUTING PROTOCOL

BABYLON-60 enforces a rigid Thermodynamic Routing matrix based on Exergy constraints to prevent AI agents from "Context Rot" and limerence loops.

- **UltraThink (P0 Singularity):** Reserved EXCLUSIVELY for cascading failures, system-level security incidents, and irreversible architectural collapses. Maximum exergy consumed.
- **Deep Research:** Used when the system lacks sufficient domain information (e.g., state of the art surveys, new APIs).
- **Deep Think:** For architectural tradeoff resolution and multi-variable constraint problems.
- **Standard (Flash):** The baseline mode for execution, editing ASTs, and manipulating DB states. Enforces Zero-Anergy.

---

## ▀▄ DEPLOYMENT INVARIANTS

**BABYLON-60 Operates under Strict Physical Laws (Singularity Nexus):**

1. **Cloudflare-Only Perimeter:** Absolute prohibition of Vercel ecosystems (`vercel.json`, `@vercel/*`). All edge/front deployments MUST target Cloudflare Pages/Workers (`wrangler.toml`). Violation triggers P0 Abort due to thermodynamic fracture.
2. **SQLite WAL Concurrency:** Concurrent thread interactions mandate strict connection factors (`busy_timeout: 5000ms`, `WAL` mode active) to eradicate deadlocks.
3. **No Hidden Entropy:** If state isn't in the git working tree, it does not causally exist (Axiom AX-041).

---

## ▀▄ INSTALLATION & TOPOLOGICAL DEPLOYMENT

**Default Stance:** Zero daemons. Core `cortex-persist` installs the `SQLite WAL` engine, SAGA guards, and cryptographic ledgers.

```bash
pip install cortex-persist
```

### ⚙️ Domain Substrates (Expansion Vectors)

> **WARNING:** Each flag physically mutates the machine's footprint. Inject strictly what is required to prevent thermodynamic degradation (Anergy).

| Vector | Payload (Physical Footprint) | Execution Matrix (C5-REAL) |
| :--- | :--- | :--- |
| `[embeddings]` | `sentence-transformers` (~120MB weights), `onnxruntime`. | **Local Vector Engine:** Deterministic indexing and cosine similarity. Zero network calls. Pure CPU/GPU inference. |
| `[knowledge]` | `chromadb` (C++ bindings). Generates `.chroma/` dir. | **Ontological Sync:** Long-term semantic retention. BFT validation of retrieved knowledge graphs. |
| `[api,mcp,daemon]` | `fastapi`, `uvicorn`, `mcp-sdk`. Opens local ports (e.g. `8765`). | **Network Gateway:** Mounts BABYLON-60 as a Sovereign MCP Server. Exposes REST/MCP endpoints for external Swarm mutation. |
| `[cloud]` | C-bindings: `asyncpg`, `redis`, `qdrant-client`. | **Distributed Scale:** Displaces local SQLite WAL consensus to external PostgreSQL/Qdrant clusters. |
| `[secure]` | `keyring` (OS-native bind), `cryptography` (AES-GCM). | **Vault:** Hard-links BABYLON-60 to the Secure Enclave (macOS Keychain) or TPM. Mandatory for financial tokens or keys. |
| `[acceleration]` | Pre-compiled Rust FFI wheels. Bypasses Python GIL. | **Hyper-Throughput:** Enables LEGION-10k mode. Sustains >390k operations/sec under extreme asymmetric load. |

```bash
# Example: Injecting full physical capabilities
pip install "cortex-persist[embeddings,secure,acceleration]"
```

---

## ▀▄ NATIVE MCP INTEGRATION

BABYLON-60 acts as a **Sovereign MCP Server**, serving deterministic cryptographic states to external tools (Claude Desktop, custom swarms):

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

## ▀▄ EPISTEMIC EVALUATION & STANDARDIZATION

> **BABYLON-60 no debería evaluarse por la calidad de las respuestas que produce, sino por las propiedades que garantiza sobre el proceso que las produce.**

The success criteria for this architecture is not *"Is BABYLON-60 smarter than an LLM?"* but rather: **"Can a BABYLON-60 implementation formally prove it preserves its invariants for any valid execution?"**

To decouple the ecosystem's evolution from underlying LLM volatility, BABYLON-60 governs its growth through a rigorous standard discipline:

- **Core Specification**: Invariants, semantics, and execution model.
- **CEP (BABYLON-60 Enhancement Proposals)**: Evolution proposals demanding formal impact arguments.
- **Reference Kernel**: Minimal implementation serving as an executable specification.
- **Conformance Levels**: Objective compliance tiers (e.g., Core, Verified Provenance, Full Trust Algebra).
- **Proof Obligations Registry**: Properties every component must formally demonstrate.

---

## ▀▄ DOCUMENTATION & REAL-WORLD C5-REAL TRACES

| Resource | Description |
| :--- | :--- |
| [SECURITY_TRUST_MODEL.md](docs/SECURITY_TRUST_MODEL.md) | Cryptographic invariants & guarantees |
| [AGENTS.md](AGENTS.md) | Substrate directives for autonomous orchestration |
| [APEX_CORE.md](cortex/agents/primitives/APEX_CORE.md) | The 100 Sovereign Execution Primitives |
| [API Reference](docs/api.md) | SDK primitives and REST endpoints |
| [MCP Integration](docs/mcp.md) | MCP server setup and tool catalog |

---

## ▀▄ AUDIT STATUS (2026-06-30)

> Full audit report: [`FINAL_AUDIT.md`](FINAL_AUDIT.md) — commit `82d755d41`

| Vector | Result |
| :--- | :--- |
| Static Analysis (Ruff) | ✅ 0 violations remaining |
| Security (Bandit) | ✅ 0 HIGH · 0 MEDIUM |
| Dependency CVEs (pip-audit) | ✅ Active API upgraded (10 CVEs remaining in ML packages) |
| Test Suite (3,886 tests) | ✅ 3,845 passed · 0 failed |
| Rust Audit (57 crates) | ✅ 0 advisories |
| SQLite Integrity | ✅ ok · WAL mode active |
| Ledger Hash Chain | ⚠️ `merkle_roots` not bootstrapped |
| Vector Extension (sqlite-vec) | ⚠️ `vec0` not loaded at startup |

---

```text
AESTHETIC:    INDUSTRIAL NOIR 2026 (#0A0A0A / #2B3BE5)
EPISTEMOLOGY: C5-REAL — Cryptographically Verified Reality
CORE TENET:   Generative output is conjecture. Evidence is absolute.
THROUGHPUT:   ~390k Agents/Sec (Rust-FFI, GIL-free)
COMMIT:       60f67a02a | branch: wave4-reality-loop-bridge
UPDATED:      2026-06-30 — Full-Spectrum Audit · SAGA Write-Path · UltraThink Routing
```

> **LICENSE:** Apache-2.0 | **OPERATOR:** borjamoskv | [cortexpersist.org](https://cortexpersist.org) | [Sponsor](https://github.com/sponsors/borjamoskv)
