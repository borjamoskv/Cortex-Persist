# CORTEX Persist

**Tamper-evident memory and decision lineage for AI agents.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)

CORTEX is trust infrastructure for AI agents.

It sits between your runtime and your memory layer, making facts, decisions, and derived state tamper-evident. If stored context changes after the fact, verification fails. If you need to explain what an agent knew, when it knew it, and what it did next, CORTEX gives you a cryptographic trail instead of an anecdote.

Built for autonomous systems that need more than "the model said so."

## Why CORTEX

LLMs do not produce trustworthy state by default.

Once an agent reads context, stores memory, calls tools, or makes a decision, that state can drift, be overwritten, or be silently mutated by downstream systems. CORTEX adds a cryptographic evidence layer on top of your existing memory stack so that important state becomes verifiable instead of anecdotal.

## What it does

- **Tamper-evident memory:** append-only ledger for facts, decisions, and state transitions.
- **Hash-linked records:** SHA-256 chaining across stored entries.
- **Batch integrity proofs:** Merkle checkpoints for efficient verification at scale.
- **Deterministic audit exports:** reproducible evidence for internal review and regulated workflows.
- **Drop-in positioning:** works on top of existing memory stores instead of replacing your stack.

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

## Use cases

* **Autonomous agents:** prove what an agent knew when it made a decision.
* **Multi-agent systems:** trace state propagation across agents and workflows.
* **Compliance-heavy environments:** produce audit trails for finance, security, and regulated operations.
* **Post-incident forensics:** detect silent mutation, tampering, or replayed state.
* **Trust-sensitive AI products:** ship memory with evidence, not vibes.

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

| Operation         | Median  | P95     | Notes                                |
| ----------------- | ------- | ------- | ------------------------------------ |
| Memory write      | ~18 ms  | ~35 ms  | Local SQLite + SHA-256 hashing       |
| Verify record     | ~5 ms   | ~12 ms  | Single-block hash validation         |
| Merkle checkpoint | ~85 ms  | ~140 ms | Aggregating 10k records              |
| Report export     | ~400 ms | ~800 ms | Lineage traversal and PDF generation |

## Architecture

CORTEX integrates as a Python SDK or a standalone REST/MCP gateway.

```text
[ Agent Runtime / Workflow Engine ]
                │
                ▼
[ CORTEX Persist ]
  ├─ append-only ledger
  ├─ hash chaining
  ├─ Merkle checkpoints
  └─ verification / audit export
                │
                ▼
[ SQLite / AlloyDB / Existing Memory Store ]
```

## Documentation

* [Architecture](docs/architecture.md)
* [API Reference](docs/api.md)
* [Security & Trust Model](docs/SECURITY_TRUST_MODEL.md)
* [Benchmarks](docs/benchmarks.md)
* [Contributing](CONTRIBUTING.md)
