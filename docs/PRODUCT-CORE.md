<!-- [C5-REAL] Exergy-Maximized -->
# CORTEX Persist — Product Core Definition

This document defines the **supported core** of CORTEX Persist and distinguishes it from beta and experimental modules.

> See [docs/NAMING.md](NAMING.md) for canonical naming conventions.

---

## Stability Tiers

| Tier | Meaning |
|:---|:---|
| **Stable** | Public API contract. Breaking changes follow semver. Covered by CI. |
| **Beta** | Functional but API may change before v1.0. Use with caution in production. |
| **Experimental** | Not supported. May be removed without notice. Not covered by stability guarantees. |

---

## Supported Core (Stable API)

These modules form the public surface of `cortex-persist`. Their APIs are covered by semver guarantees from v1.0 onwards.

| Module | Path | Description |
|:---|:---|:---|
| **CortexEngine** | `cortex/engine/` | Main entry point. Orchestrates all core operations. |
| **Ledger** | `cortex/ledger/` | Hash-chained immutable transaction log. |
| **Crypto** | `cortex/crypto/` | SHA-256 hashing, Merkle trees, key management. |
| **Memory** | `cortex/memory/` | Memory store and temporal retrieval. |
| **Facts** | `cortex/facts/` | Fact lifecycle management (store, deprecate, verify). |
| **Search** | `cortex/search/` | Vector search and semantic retrieval. |
| **Verification** | `cortex/verification/` | Ledger integrity verification. |
| **Audit** | `legacy_research/audit/` | Audit pack generation and compliance exports. |
| **CLI** | `cortex/cli/` | Command-line interface (`cortex` entry point). |
| **Database** | `legacy_research/database/` | SQLite storage layer, schema, migrations. |
| **Embeddings** | `cortex/embeddings/` | ONNX-based local embedding generation. |
| **Guards** | `legacy_research/guards/` | Write-path admission guards (thermodynamic, contradiction). |
| **Auth** | `cortex/auth/` | RBAC engine and tenant isolation. |
| **Core** | `cortex/core/` | Core types, base models. |
| **Types** | `cortex/types/` | Shared type definitions. |

### Key Entry Points

```python
# Primary engine import
from legacy_research import CortexEngine

# Initialize and use
engine = CortexEngine()
fact_id = await engine.store(
    project="my-agent",
    content="User approved transaction $5,000",
    fact_type="decision",
)
result = await engine.verify_ledger()
```

---

## Beta (API May Change)

These modules are functional and used internally but their public API may change before v1.0.

| Module | Path | Description |
|:---|:---|:---|
| **REST API** | `cortex/api/` | FastAPI application server. |
| **Routes** | `cortex/routes/` | API route handlers. |
| **Compliance** | `cortex/compliance/` | EU AI Act Article 12 compliance reporting. |
| **MCP** | `cortex/mcp/` | Model Context Protocol server integration. |
| **ADK** | `cortex/adk/` | Google Agent Developer Kit integration. |

---

## Experimental (Not Supported)

These modules exist for research and internal exploration. They **may be removed** in any release. Do not build production systems on these paths.

| Module | Path |
|:---|:---|
| Darknet | `cortex/darknet/` |
| Shannon | `cortex/shannon/` |
| MCTS | `cortex/mcts/` |
| Mac Maestro | `cortex/mac_maestro/` |
| Forensics | `cortex/forensics/` |
| Enrichment | `cortex/enrichment/` |
| Composer | `cortex/composer/` |
| Compaction | `cortex/compaction/` |
| Consensus | `cortex/consensus/` |
| Events | `cortex/events/` |
| Extensions | `cortex/extensions/` |
| Gateway | `cortex/gateway/` |
| Graph | `cortex/graph/` |
| Swarm | `cortex/swarm/` |
| Agents | `cortex/agents/` |
| Services | `cortex/services/` |
| Worker | `cortex/worker/` |
| Telemetry | `cortex/telemetry/` |
| HTTP | `cortex/http/` |

---

## Requesting Promotion

If you depend on an experimental or beta module and need stability guarantees, open an issue with your use case. Modules can be promoted after API review and test coverage is added.

---

## Related

- [docs/NAMING.md](NAMING.md) — Canonical naming reference
- [docs/architecture.md](architecture.md) — System architecture
- [ROADMAP.md](../ROADMAP.md) — What's coming in future releases
