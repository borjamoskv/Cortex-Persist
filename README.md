<p align="center">
  <img src="assets/marketing/social-preview.png" alt="CORTEX Persist — Tamper-evident memory for AI agents" width="720">
</p>

<h1 align="center">CORTEX Persist</h1>

<p align="center">
  <strong>Cryptographically trace what your AI agent knew.</strong>
</p>

<p align="center">
  Tamper-evident memory and decision lineage for AI agents.&nbsp;
  <br>
  Local-first. SHA-256 hash-chained. Merkle-sealed. Audit-ready.
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/Cortex-Persist/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/Cortex-Persist?style=social" alt="GitHub Stars"></a>&nbsp;&nbsp;
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"></a>&nbsp;
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>&nbsp;
  <a href="https://github.com/borjamoskv/Cortex-Persist/actions"><img src="https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg" alt="CI"></a>&nbsp;
  <a href="https://codecov.io/gh/borjamoskv/Cortex-Persist"><img src="https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg" alt="Codecov"></a>&nbsp;
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg" alt="PyPI"></a>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> · <a href="docs/api.md">API</a> · <a href="docs/SECURITY_TRUST_MODEL.md">Security Model</a> · <a href="ROADMAP.md">Roadmap</a> · <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

CORTEX is trust infrastructure for AI agents. It sits between your runtime and your memory layer, making facts, decisions, and derived state tamper-evident. If stored context changes after the fact, verification fails. If you need to explain what an agent knew, when it knew it, and what it did next, CORTEX gives you a cryptographic trail instead of an anecdote.

## Why not logs / observability?

| Feature | Logs & Observability | CORTEX Persist (Trust Layer) |
| :--- | :--- | :--- |
| **Trust Model** | "Trust the process" | **"Verify the evidence"** |
| **Tamper Detection** | Weak (DB mutation is silent) | **Cryptographic** (SHA-256 + Merkle) |
| **Compliance Proof** | Requires manual reconstruction | **O(1) Portable JSON Audit Packs** |
| **Agent Liability** | Ambiguous context reconstruction | **Mathematically defensible lineage** |

> Logs tell you what happened. CORTEX adds cryptographic evidence for what the agent knew, when it knew it, and whether later tampering is detectable along the verified chain. [**Review a real verification proof.**](docs/examples/audit_pack_evidence_demo.json)

## Use Cases

1. **Autonomous Agents:** Prove exactly what context an agent had when making a critical, irreversible decision (e.g. executing a trade, sending a legal email).
2. **Multi-Agent Systems:** Trace state propagation across agents and workflows.
3. **Compliance-Heavy Environments:** Produce audit trails for finance, security, and regulated operations.
4. **Post-incident forensics:** detect silent mutation, tampering, or replayed state.
5. **Trust-sensitive AI products:** ship memory with evidence, not vibes.

## Why CORTEX? (Not just another Vector DB or Logger)

Traditional logging and standard vector stores fail the epistemic containment test. If an agent hallucinates, or if a database is mutated passively, you lose structural trust in the machine. CORTEX makes mutation mathematically defensible.

| Feature                    | Standard Logs (Datadog/ELK) | Standard Vector DB (Pinecone/Qdrant) | **CORTEX Persist**                        |
|:---------------------------|:----------------------------|:-------------------------------------|:------------------------------------------|
| **Primary Goal**           | Observability & Debugging   | Semantic Search & RAG                | **Tamper-Evident Cognitive Lineage**      |
| **Write Integrity**        | Overwritable / Editable     | Silent CRUD operations               | **Append-Only + Cryptographic Hash**      |
| **Fact Mutability**        | Easy (API/Admin access)     | Easy (API/Admin access)              | **Tamper-evident** (verification reveals mutation) |
| **Evidence Export**        | Text dumps                  | JSON extracts                        | **Zero-Trust Sealed Audit Packs**         |

> **See a real artifact**: [View Exported Audit Pack](examples/audit_proof_artifact.json)

### What CORTEX does NOT replace (Non-Goals)

- **CORTEX is not a Semantic Search primary DB:** Continue using Qdrant, Pinecone, or Milvus for purely ephemeral RAG chunks. CORTEX stores the *decisions* and core *facts*.
- **CORTEX is not an Observability Platform:** Continue using Datadog or ELK for server metrics, APM, and basic string logs.
- **CORTEX does not stop hallucinations:** A cryptographically logged lie from an LLM is still a lie. It is merely an *auditable* lie, flagged if it contradicts prior sealed facts.

## Deployment Matrix

- **Tamper-evident memory:** append-only ledger for facts, decisions, and state transitions.
- **Hash-linked records:** SHA-256 chaining across stored entries.
- **Batch integrity proofs:** Merkle checkpoints for efficient verification at scale.
- **Deterministic audit exports:** reproducible evidence for internal review and regulated workflows.
- **Drop-in positioning:** works on top of existing memory stores instead of replacing your stack.

| Environment | Status | Storage / Scaling |
| :--- | :--- | :--- |
| **Local-Only** | ✅ **Stable local-first core** | SQLite + WAL + built-in Vector Search. Best-supported path today. |
| **Self-Hosted** | 🟡 **Beta** | Multi-tenant. API-driven. Redis cache. Pluggable to your infra. |
| **Cloud-Ready** | ⏳ **Partial / Roadmap** | Postgres/Qdrant/Turso code exists in-tree; managed cloud posture remains incomplete. |

## Product Core

The supported core modules are: **engine**, **ledger**, **crypto**, **memory**, **facts**, **search**, **verification**, **audit**, **CLI**, **database**, **embeddings**, **guards**, **auth**, **core**, and **types**.

See [docs/PRODUCT-CORE.md](docs/PRODUCT-CORE.md) for the full stability tier breakdown (Stable / Beta / Experimental).

## 90-second demo

```bash
# 1. Start the ledger
$ cortex init

# 2. Store a memory
$ cortex memory store risk-bot "Transaction flagged: IP mismatch"
[+] Fact stored. Ledger hash: 8f4a2b9e...

# 3. Verify the stored fact
$ cortex verify 1
[✔] VERIFIED: Fact chain intact.

# 4. Tamper attempt (direct DB mutation)
$ sqlite3 cortex.db "UPDATE facts SET content='Transaction approved' WHERE id='8f4a2b9e'"

# 5. Ledger verification
$ cortex trust-ledger verify
[✘] TAMPER DETECTED: Hash mismatch at block 8f4a2b9e

# 6. Generate a compliance snapshot
$ cortex compliance-report
```

> 🐍 **Python demo:** For a self-contained Python script that walks through the full core flow, see [`examples/demo_canonical.py`](examples/demo_canonical.py).

## Quickstart

Start with the smallest supported flow and get to audit evidence fast.

The supported PyPI base flow is `install -> init -> store -> verify`.
Semantic search, MCP/server flows, and other extended surfaces may require optional extras or a fuller local runtime.

### Path A: Install from PyPI *(preferred)*

```bash
pip install cortex-persist
cortex init
cortex memory store risk-bot "Transaction flagged: IP mismatch"
cortex trust-ledger verify
```

For local semantic embeddings, Chroma-backed knowledge sync, or JIT acceleration, add the optional extras you actually need:

```bash
pip install "cortex-persist[embeddings]"
pip install "cortex-persist[knowledge]"
pip install "cortex-persist[acceleration]"
pip install "cortex-persist[platform]"       # macOS keychain support
pip install "cortex-persist[api,mcp,daemon,authoring]"  # optional server surfaces
```

### Path B: Install from Source *(development)*

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cortex init
cortex memory store risk-bot "Transaction flagged: IP mismatch"
cortex trust-ledger verify
```

See [docs/installation.md](docs/installation.md) for full installation options and platform-specific notes.

## Integration

CORTEX wraps your existing state management. It does not replace your embeddings or vector search.

```python
import asyncio
from cortex import CortexEngine

async def main() -> None:
    engine = CortexEngine()

    fact_id = await engine.store(
        project="fin-fraud-bot",
        content="User approved transaction $5,000",
        fact_type="decision",
        tenant_id="customer-123",
    )

    result = await engine.verify_ledger()
    assert result.get("valid") is True

asyncio.run(main())
```

## Performance

*Typical execution on a standard cloud instance (4 vCPU, 16 GB RAM).*

| Operation | Median | P95 | Notes |
| :--- | :--- | :--- | :--- |
| **Memory Write** | ~18 ms | ~35 ms | Local SQLite + SHA-256 |
| **Verify Record** | ~5 ms | ~12 ms | Single block validation |
| **Merkle Checkpoint** | ~85 ms | ~140 ms | Aggregating 10k records |
| **Report Export** | ~400 ms | ~800 ms | Lineage traversal |

---

## Threat Model Summary (Trust Boundaries)

CORTEX is governed by a strict zero-trust philosophy regarding generative AI output.
- **Generative Output is Conjecture:** We treat all LLM output as thermodynamically unstable (`Void-State`). It only becomes durable memory *after* crossing the deterministic verification membrane.
- **SQL Sandboxing:** Agents cannot run arbitrary queries; mutations must pass through rigid schema validation and formal AST checkpoints.
- **Tamper Evidence over Access Control:** Instead of just hoping admins don't edit rows, we hash-chain the ledger so any manual modification invalidates the mathematical proof of the memory thread.

> Read the exhaustive cryptographic guarantees in our [Security & Trust Model](docs/SECURITY_TRUST_MODEL.md).

---

## Documentation

- [**Security & Trust Model**](docs/SECURITY_TRUST_MODEL.md) — Cryptographic invariants & guarantees.
- [**Roadmap**](ROADMAP.md) — Deployment phases and scaling logic.
- [**API Reference**](docs/api.md) — SDK primitives and REST endpoints.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).

*Built by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*

---
## Verification Membrane (primitive)
- Boundary where untrusted input becomes sealed, verifiable state.
- Nothing crosses unverified.
- Every write produces proof.

## Strict mode (recommended)
Enforce:
- reject unverifiable writes
- require idempotency_key
- enforce schema hash consistency

## Proof of tampering (should fail)
```bash
# example manual mutation (depends on backend)
sqlite3 cortex.db "UPDATE facts SET content='Approved' WHERE id=1"

cortex verify
```
Expected (conceptual):
```
[✘] TAMPER DETECTED: hash mismatch
```

---
## Multi-language summary
EN: Tamper-evident memory for AI agents. Proof at decision time.
ES: Memoria a prueba de manipulaciones para agentes de IA. Prueba del estado en tiempo de decisión.
ZH: 面向 AI 代理的防篡改记忆。证明决策时刻的状态。
