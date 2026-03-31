# CORTEX Persist

**Tamper-evident memory and decision lineage for AI agents.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/cortex/branch/master/graph/badge.svg)](https://codecov.io/gh/borjamoskv/cortex)
[![PyPI](https://img.shields.io/pypi/v/cortex-persist.svg)](https://pypi.org/project/cortex-persist/)

CORTEX is trust infrastructure for AI agents.

It sits between your runtime and your memory layer, making facts, decisions, and derived state tamper-evident. If stored context changes after the fact, verification fails. If an auditor asks what an agent knew and when it knew it, CORTEX gives you a cryptographic trail instead of an anecdote.

Use it when "probably correct" is an unacceptable risk.

---

## Why CORTEX

LLMs do not produce trustworthy state by default.

Once an agent reads context, calls tools, or makes a decision, that state can drift, be overwritten, or be silently mutated. CORTEX adds an immutable cryptographic evidence layer over your existing memory stack so that your system's memory becomes verifiable instead of anecdotal.

---

## What it does

- **Tamper-evident memory:** Append-only ledger for facts, decisions, and state transitions.
- **Hash-linked records:** SHA-256 chaining across stored entries.
- **Batch integrity proofs:** Merkle checkpoints for efficient verification at scale (10k+ blocks/sec).
- **Deterministic audit exports:** Reproducible evidence for internal review and regulated workflows (EU AI Act).
- **Drop-in positioning:** Works over existing vector and SQL stores without replacing your stack.

---

## Use cases

- **Autonomous agents:** Prove exactly what an agent knew when it made a critical decision.
- **Multi-agent systems:** Trace state propagation across complex agent workflows.
- **Compliance environments:** Produce verifiable audit trails for finance, security, and regulated healthcare operations.
- **Post-incident forensics:** Detect silent mutation, data tampering, or replayed state.
- **Trust-sensitive AI products:** Ship memory with immutable cryptographic evidence, not vibes.

---

## Architecture

```text
[ Agent Runtime / Workflow Engine ]
                │
                ▼
[ CORTEX Persist ]
  ├─ Append-only Ledger
  ├─ SHA-256 Hash Chaining
  ├─ Merkle Checkpoints
  └─ Audit Verification Engine
                │
                ▼
[ SQLite / AlloyDB / Existing Vector Store ]
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
    
    # Verify proof of integrity against the ledger
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
