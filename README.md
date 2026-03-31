# CORTEX Persist

**Tamper-evident memory and decision lineage for AI agents.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/cortex/branch/master/graph/badge.svg)](https://codecov.io/gh/borjamoskv/cortex)
[![PyPI](https://img.shields.io/pypi/v/cortex-persist.svg)](https://pypi.org/project/cortex-persist/)

CORTEX is trust infrastructure for AI agents.

It sits between your runtime and your memory layer, making facts, decisions, and derived state tamper-evident. If stored context changes after the fact, verification fails. If you need to explain what an agent knew, when it knew it, and what it did next, CORTEX gives you a cryptographic trail instead of an anecdote.

Use it when “probably correct” is not enough.

---

## Why CORTEX

LLMs do not produce trustworthy state by default.

Once an agent reads context, stores memory, calls tools, or makes a decision, that state can drift, be overwritten, or be silently mutated by downstream systems. CORTEX adds a cryptographic evidence layer on top of your existing memory stack so that important state becomes verifiable instead of anecdotal.

---

## What it does

- **Tamper-evident memory:** append-only ledger for facts, decisions, and state transitions.
- **Hash-linked records:** SHA-256 chaining across stored entries.
- **Batch integrity proofs:** Merkle checkpoints for efficient verification at scale.
- **Deterministic audit exports:** reproducible evidence for internal review and regulated workflows.
- **Drop-in positioning:** works on top of existing memory stores instead of replacing your stack.

---

## Use cases

- **Autonomous agents:** prove what an agent knew when it made a decision.
- **Multi-agent systems:** trace state propagation across agents and workflows.
- **Compliance-heavy environments:** produce audit trails for finance, security, and regulated operations.
- **Post-incident forensics:** detect silent mutation, tampering, or replayed state.
- **Trust-sensitive AI products:** ship memory with evidence, not vibes.

---

## Architecture

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

---

## Quickstart

```bash
# 1. Install & Initialize
pip install cortex-persist
cortex init

# 2. Store a memory (SHA-256 hashed and chained)
cortex memory store --agent "risk-bot" --content "Transaction flagged: IP mismatch"

# 3. Verify integrity (detects manual database tampering)
cortex verify ledger
```

---

## Integration

```python
import asyncio
from cortex import CortexEngine

async def main():
    engine = CortexEngine()
    
    # Store with cryptographic receipt
    receipt = await engine.store_fact(
        content="User approved transaction $5,000",
        fact_type="decision"
    )
    
    # Verify proof of integrity
    assert await engine.verify(receipt.hash) == True

asyncio.run(main())
```

---

## Performance

*Standard cloud instance (4 vCPU, 16GB RAM).*

| Operation | Median | P95 | Notes |
|:---|:---|:---|:---|
| **Memory Write** | ~18 ms | ~35 ms | Local SQLite + SHA-256 |
| **Verify Record** | ~5 ms | ~12 ms | Single block validation |
| **Merkle Seal** | ~85 ms | ~140 ms | 10k records checkpoint |
| **Audit Export** | ~400 ms | ~800 ms | Lineage traversal & PDF |

---

## Documentation

- [**Architecture**](docs/architecture.md) — Merkle-tree seals and hash-chains.
- [**Security & Trust**](docs/SECURITY_TRUST_MODEL.md) — Cryptographic invariants.
- [**API Reference**](docs/api.md) — Full SDK and CLI documentation.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).

*Built by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
