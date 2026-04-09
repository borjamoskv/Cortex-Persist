# CORTEX Persist Architecture

This page is the repo-versioned architecture summary for the public product surface.

## Product Surface

| Surface | Current Contract | Status |
| :--- | :--- | :--- |
| Distribution name | `cortex-persist` | Public contract |
| Public Python import | `cortex_persist` | Public contract |
| Internal runtime package | `cortex` | Internal implementation detail |
| CLI entrypoint | `cortex` | Supported core |
| API app | `cortex.api:app` | Self-hosted beta |
| MCP server | `python -m cortex.mcp` | Broader repo surface, not supported core |

The table above shows how to interpret the repo entrypoints. The current support boundary is still defined by [Supported Core](supported-core.md), not by every executable surface in-tree.

## High-Level Flow

1. Facts or decisions enter through CLI, API, MCP, or internal services.
2. Guards and deterministic validation run before persistence.
3. Ledger continuity and attribution metadata are emitted.
4. Durable storage and secondary index updates commit together or abort together.
5. Verification tooling checks continuity after the fact.

Today, the supported operator path is the local-first CLI core. API and MCP remain useful architecture surfaces, but they should be read as beta or broader repo capability unless [Supported Core](supported-core.md) says otherwise.

## Architectural Groupings

The current repository uses a six-part grouping model. The two entrypoints below hold the taxonomy and the trust-capability interpretation of that model:

- [System Map](system-map.md)
- [CORTEX Native Technologies](cortex-native-technologies.md)

## Critical Paths

These areas deserve extra care during review:

- `cortex/engine/`
- `cortex/memory/`
- `cortex/guards/`
- `cortex/verification/`
- `cortex/routes/`
- `cortex/services/`
- `migrations/`

## Deployment Direction

| Deployment posture | Status |
| :--- | :--- |
| Local-first SQLite | Most mature |
| Operator-managed self-hosted API | Beta |
| Larger distributed/cloud posture | Roadmap |

## Related References

- [Supported Core](supported-core.md)
- [Security & Trust Model](SECURITY_TRUST_MODEL.md)
- [API Reference](api.md)
- [Operations](OPERATIONS.md)
- [ENTERPRISE_READINESS.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/ENTERPRISE_READINESS.md)
