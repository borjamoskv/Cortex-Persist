# CORTEX Persist

**Cryptographic memory integrity, audit trails, and verifiable lineage for AI agents.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/cortex/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/cortex/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/cortex/branch/master/graph/badge.svg)](https://codecov.io/gh/borjamoskv/cortex)
[![PyPI](https://img.shields.io/pypi/v/cortex-persist.svg)](https://pypi.org/project/cortex-persist/)

CORTEX is a **drop-in trust layer** for AI memory. It enforces cryptographic integrity on top of any storage (Mem0, Zep, or custom), ensuring agent state and decisions remain tamper-evident and audit-ready.

---

### How CORTEX fits

*   **For Builders** → Add tamper-evident memory to existing agents in 30 seconds.
*   **For Compliance** → Export deterministic audit evidence for regulatory requirements (EU AI Act).
*   **For Infra Teams** → Wrap your current vector store without replacing your embeddings or logic.

---

### Quickstart

```bash
# 1. Install & Initialize
pip install cortex-persist
cortex init

# 2. Store a memory (SHA-256 hashed and chained)
cortex memory store --agent "risk-bot" --content "Transaction flagged: IP mismatch"

# 3. Verify integrity (detects manual database tampering)
cortex verify ledger
```

**What just happened?**
-   **Immutable Ledger**: Fact stored in an append-only cryptographic log.
-   **Hash Chaining**: Record SHA-256 chained to the previous block.
-   **Merkle Seal**: Entire state sealed with a verifiable proof of lineage.

---

### Integration

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

### Performance

*Standard cloud instance (4 vCPU, 16GB RAM).*

| Operation | Median | P95 | Notes |
|:---|:---|:---|:---|
| **Memory Write** | ~18 ms | ~35 ms | Local SQLite + SHA-256 |
| **Verify Record** | ~5 ms | ~12 ms | Single block validation |
| **Merkle Seal** | ~85 ms | ~140 ms | 10k records checkpoint |
| **Audit Export** | ~400 ms | ~800 ms | Lineage traversal & PDF |

---

### Documentation

- [**Architecture**](docs/architecture.md) — Merkle-tree seals and hash-chains.
- [**Security & Trust**](docs/SECURITY_TRUST_MODEL.md) — Cryptographic invariants.
- [**API Reference**](docs/api.md) — Full SDK and CLI documentation.

---

### License

Apache License 2.0. See [LICENSE](LICENSE).

*Built by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
