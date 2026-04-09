# CORTEX Persist Security & Trust Model

This page is the repo-versioned summary of what CORTEX does and does not guarantee.

## Trust Boundary

CORTEX sits between agent/runtime behavior and durable storage. Its goal is to turn facts, decisions, and state transitions into tamper-evident records instead of leaving them as mutable application state or reconstructable logs.

The current supported operator path is the local-first CLI core. The self-hosted beta API and the MCP server use the same trust concepts, but they are broader repo surfaces than the minimum support contract documented in [Supported Core](supported-core.md).

## Core Guarantees

- Generated output should be validated before it becomes durable state.
- Ledger continuity should make silent mutation detectable after the fact.
- Public data paths should remain tenant-aware by default.
- Sensitive payload handling should preserve encryption and audit expectations where configured.
- Verification commands should be available independently from the workflow that created the record.

## Non-Guarantees

- CORTEX does not make a model output true.
- CORTEX does not replace access control or operator hygiene.
- CORTEX does not by itself create legal or regulatory compliance.
- CORTEX is tamper-evident, not magically tamper-proof.

## Write-Path Expectations

1. A proposal enters through CLI, API, MCP, or an internal service.
2. Guards and deterministic validation run before persistence.
3. The ledger records continuity and attribution metadata.
4. Persistence commits only after validation succeeds.
5. Failed write-path steps should abort without leaving partial durable state behind.

## Verification Paths

Use these operator checks for the supported local surface:

```bash
cortex verify <FACT_ID>
cortex trust-ledger verify --full
```

For self-hosted beta API-backed consumers, use the same verification concepts through the exposed endpoints and the thin clients documented in [API Reference](api.md).

## Related References

- [Architecture](architecture.md)
- [Supported Core](supported-core.md)
- [Operations](OPERATIONS.md)
- [SECURITY.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/SECURITY.md)
- [AGENTS.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/AGENTS.md)
