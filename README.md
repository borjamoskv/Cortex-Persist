# CORTEX Persist

**Tamper-evident memory and decision lineage for AI agents.**

CORTEX-Persist is a local-first memory and trust layer for AI systems that need persistent context, cryptographic lineage, and audit-ready history.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg)](https://codecov.io/gh/borjamoskv/Cortex-Persist)
[![PyPI](https://img.shields.io/pypi/v/cortex-persist.svg)](https://pypi.org/project/cortex-persist/)

CORTEX is trust infrastructure for AI agents. It sits between your runtime and your memory layer, making facts, decisions, and derived state tamper-evident. If stored context changes after the fact, verification fails. If you need to explain what an agent knew, when it knew it, and what it did next, CORTEX gives you a cryptographic trail instead of an anecdote.

## Why not logs / observability?

| Feature | Logs & Observability | CORTEX Persist (Trust Layer) |
| :--- | :--- | :--- |
| **Trust Model** | "Trust the process" | **"Verify the evidence"** |
| **Tamper Detection** | Weak (DB mutation is silent) | **Cryptographic** (SHA-256 + Merkle) |
| **Compliance Proof** | Requires manual reconstruction | **O(1) Portable JSON Audit Packs** |
| **Agent Liability** | Ambiguous context reconstruction | **Mathematically defensible lineage** |

> Logs tell you what happened. CORTEX proves exactly what the agent knew, when it knew it, and mathematically guarantees the record hasn't been altered since. [**Review a real verification proof.**](docs/examples/audit_pack_evidence_demo.json)

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
| **Fact Mutability**        | Easy (API/Admin access)     | Easy (API/Admin access)              | **Impossible** (Breaks hash chain)        |
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
| **Local-Only** | ✅ **Production-Ready** | SQLite + WAL + built-in Vector Search. Perfect for single daemons. |
| **Self-Hosted** | 🟡 **Beta** | Multi-tenant. API-driven. Redis cache. Pluggable to your infra. |
| **Cloud-Ready** | ⏳ **Roadmap** | AlloyDB/PostgreSQL + Qdrant. For distributed massive swarms. |

## 90-second demo

```bash
# 1. Start the ledger
$ cortex init

# 2. Store a memory
$ cortex memory store --agent "risk-bot" --content "Transaction flagged: IP mismatch"
[+] Fact stored. Ledger hash: 8f4a2b9e...

# 3. Verify integrity
$ cortex verify record 8f4a2b9e
[✔] VERIFIED: Hash chain intact. Merkle root sealed.

# 4. Tamper attempt (direct DB mutation)
$ sqlite3 cortex.db "UPDATE facts SET content='Transaction approved' WHERE id='8f4a2b9e'"

# 5. Ledger verification
$ cortex verify ledger
[✘] TAMPER DETECTED: Hash mismatch at block 8f4a2b9e

# 6. Export evidence
$ cortex compliance-report generate --format pdf
```

## Quickstart

Start logging tamper-evident memories locally in under a minute.

```bash
# 1. Install & Initialize
pip install cortex-persist
cortex init

# 2. Store a memory (SHA-256 hashed and chained to prior facts)
cortex memory store --agent "risk-bot" --content "Transaction flagged: IP mismatch"

# 3. Verify integrity (detects any manual database tampering)
cortex verify ledger
```

## Integration

CORTEX wraps your existing state management. It does not replace your embeddings or vector search.

```python
import asyncio
from cortex import CortexEngine

async def main() -> None:
    engine = CortexEngine()

    receipt = await engine.store_fact(
        content="User approved transaction $5,000",
        fact_type="decision",
        project="fin-fraud-bot",
        tenant_id="customer-123",
    )

    assert await engine.verify(receipt.hash) is True

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
