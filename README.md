# CORTEX Persist

Tamper-evident memory, audit trails, and verifiable lineage for AI agents.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/cortex/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/cortex/actions)

CORTEX is a middleware layer that enforces cryptographic integrity on top of existing AI memory stores (Mem0, Zep, Custom). It ensures that once an autonomous agent reads context or makes a decision, that state cannot be silently altered.

## Mechanics

- **Append-only ledger:** Immutable storage backed by SQLite or AlloyDB.
- **Cryptographic seals:** SHA-256 hash chains per memory record.
- **State verification:** Merkle tree checkpoints for batch integrity proofs.
- **Compliance export:** Deterministic audit reports for regulated workflows.

## 90-Second Demo

```bash
# 1. Start the ledger
$ cortex init

# 2. Store a memory
$ cortex memory store --agent "risk-bot" --content "Transaction flagged: IP mismatch"
[+] Fact stored. Ledger hash: 8f4a2b9e...

# 3. Verify integrity
$ cortex verify record 8f4a2b9e
[✔] VERIFIED: Hash chain intact. Merkle root sealed.

# 4. Tamper attempt (Direct DB mutation)
$ sqlite3 cortex.db "UPDATE facts SET content='Transaction approved' WHERE id='8f4a2b9e'"

# 5. Ledger verification
$ cortex verify ledger
[✘] TAMPER DETECTED: Hash mismatch at block 8f4a2b9e

# 6. Export evidence
$ cortex compliance-report generate --format pdf
```

## Integration

CORTEX wraps your existing state management. It does not replace your embeddings or vector search.

```python
import asyncio
from cortex import CortexEngine

async def main():
    engine = CortexEngine()
    
    # Write to tamper-evident ledger
    receipt = await engine.store_fact(
        content="User approved transaction $5,000",
        fact_type="decision",
        project="fin-fraud-bot",
        tenant_id="customer-123"
    )
    
    # Cryptographic proof verification
    assert await engine.verify(receipt.hash) == True

asyncio.run(main())
```

## Performance

*Typical execution on standard cloud instance (4 vCPU, 16GB RAM).*

| Operation | Median | P95 | Notes |
|:---|:---|:---|:---|
| Memory write | ~18 ms | ~35 ms | Local SQLite + SHA-256 hashing |
| Verify record | ~5 ms | ~12 ms | Single block hash validation |
| Merkle checkpoint | ~85 ms | ~140 ms | Aggregating 10k records |
| Report export | ~400 ms | ~800 ms | Lineage traversal & PDF generation |

## Architecture

CORTEX integrates as a standard Python SDK or a standalone REST/MCP gateway.

```text
[ Agent Framework ] -> [ CORTEX Gateway ] -> [ Target Memory Store ]
                            │
                            ├─ SHA-256 Hash Chaining
                            ├─ Merkle Checkpoints
                            └─ Cryptographic Verification
```

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Security & Trust Model](docs/SECURITY_TRUST_MODEL.md)
- [Benchmarks](docs/benchmarks.md)
- [Contributing](CONTRIBUTING.md)
