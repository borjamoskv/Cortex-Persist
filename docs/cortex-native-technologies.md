# CORTEX Native Technologies

These are the five trust capabilities that define the product surface beyond simple logging or semantic retrieval.

| Capability | What It Means | Primary Surfaces |
| :--- | :--- | :--- |
| Deterministic admission checks | Generated claims are validated before they become durable state. | `cortex/guards/`, `cortex/verification/`, `cortex/services/` |
| Hash continuity and checkpoint verification | Ledger records can be checked across events, batches, and rollback boundaries. | `cortex/memory/`, `cortex/verification/`, `cortex/compliance/` |
| Explicit uncertain and tainted memory handling | Contradictory, stale, or tainted state remains visible instead of being silently blended in. | `cortex/memory/`, `cortex/services/public_memory.py`, `cortex/verification/` |
| Rollback-aware write flows | Non-trivial state changes should abort cleanly instead of leaving partial durable state behind. | `cortex/engine/`, `cortex/services/`, `cortex/database/` |
| Isolated self-modification paths | Runtime code generation can be tested and contained before it affects durable state. | `cortex/extensions/skills/`, `cortex/extensions/sovereign/`, `cortex/extensions/swarm/` |

## Why This Matters

The point is not to replace logs, vector databases, or orchestration frameworks. The point is to add a trust layer on top of them so the resulting memory and decisions can be verified later.

## Related References

- [System Map](system-map.md)
- [Supported Core](supported-core.md)
- [Security & Trust Model](SECURITY_TRUST_MODEL.md)
- [Architecture](architecture.md)
