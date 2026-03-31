# CORTEX Persist

**Tamper-evident memory and decision lineage for AI agents.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg)](https://codecov.io/gh/borjamoskv/Cortex-Persist)
[![PyPI](https://img.shields.io/pypi/v/cortex-persist.svg)](https://pypi.org/project/cortex-persist/)

CORTEX sits between your agent runtime and your memory layer, making facts, decisions, and derived state cryptographically tamper-evident. **If an auditor asks what an agent knew and when it knew it, CORTEX gives you a hash-chained trail instead of an anecdote.**

---

## Use Cases

1. **Autonomous Agents:** Prove exactly what context an agent had when making a critical, irreversible decision (e.g. executing a trade, sending a legal email).
2. **Compliance & Regulated AI:** Export deterministic, Merkle-sealed audit trails for EU AI Act compliance, finance, or healthcare systems.
3. **Forensics & Rollbacks:** Instantly detect silent state mutations, database tampering, or poisoned vectors across your memory stack.

---

## Deployment Matrix

CORTEX is designed to scale with your trust requirements:

| Environment | Status | Storage / Scaling |
| :--- | :--- | :--- |
| **Local-Only** | ✅ **Production-Ready** | SQLite + WAL + built-in Vector Search. Perfect for single daemons. |
| **Self-Hosted** | 🟡 **Beta** | Multi-tenant. API-driven. Redis cache. Pluggable to your infra. |
| **Cloud-Ready** | ⏳ **Roadmap** | AlloyDB/PostgreSQL + Qdrant. For distributed massive swarms. |
| **Experimental** | 🔬 **Research** | Zero-Knowledge encrypted facts + Gossip network federation. |

---

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

---

## Extended Architecture & Performance

### How it works

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
[ SQLite / Remote Storage ]
```

### Performance (Local Storage)

*Standard cloud instance (4 vCPU, 16GB RAM).*

| Operation | Median | P95 | Notes |
| :--- | :--- | :--- | :--- |
| **Memory Write** | ~18 ms | ~35 ms | Local SQLite + SHA-256 |
| **Verify Record** | ~5 ms | ~12 ms | Single block validation |

---

## Documentation

- [**Security & Trust Model**](docs/SECURITY_TRUST_MODEL.md) — Cryptographic invariants & guarantees.
- [**Roadmap**](ROADMAP.md) — Deployment phases and scaling logic.
- [**API Reference**](docs/api.md) — SDK primitives and REST endpoints.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).

*Built by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
