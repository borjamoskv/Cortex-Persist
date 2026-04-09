# CORTEX Persist System Map

This page names the stable subsystem taxonomy used to describe the repository without forcing an immediate internal package rename.

| Subsystem | Role | Existing Package Surfaces |
| :--- | :--- | :--- |
| **CORTEX Hypercore** | Trust kernel, guards, ledger, and persistence boundary | `engine/`, `ledger/`, `guards/`, `verification/`, `crypto/`, `database/`, `storage/`, `security/`, `auth/` |
| **CORTEX Overmind** | Orchestration, swarm control, coordination, and agent runtime | `agents/`, `consensus/`, `gateway/`, `mcp/`, `worker/`, `extensions/swarm/`, `extensions/sovereign/`, `extensions/federation/`, `extensions/hypervisor/`, `extensions/manifold/` |
| **CORTEX Deepforge** | Synthesis, reasoning, perception, and code-generation surfaces | `composer/`, `mcts/`, `shannon/`, `extensions/llm/`, `extensions/thinking/`, `extensions/evolution/`, `extensions/training/`, `extensions/skills/`, `extensions/perception/` |
| **CORTEX Primeflow** | Execution runtime, APIs, services, event delivery, and operational flows | `api/`, `routes/`, `services/`, `events/`, `http/`, `cli/`, `telemetry/`, `extensions/automation/`, `extensions/daemon/`, `extensions/sync/`, `extensions/notifications/`, `extensions/timing/` |
| **CORTEX Coreshift** | Memory evolution, indexing, migration, audit, and state transitions | `memory/`, `facts/`, `search/`, `embeddings/`, `graph/`, `compaction/`, `enrichment/`, `migrations/`, `audit/`, `compliance/`, `forensics/` |
| **CORTEX Ouroboros** | Economic extraction, market intelligence, MEV, and dark forest forensics | `ouroboros-sniper/`, `extensions/economy/`, `extensions/trading/`, `extensions/market/` |

These names are architectural groupings over the checked-in repository. They do not change the current internal Python package layout.

## Related References

- [Architecture](architecture.md)
- [CORTEX Native Technologies](cortex-native-technologies.md)
- [Supported Core](supported-core.md)
