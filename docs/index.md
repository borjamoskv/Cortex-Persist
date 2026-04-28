# CORTEX Persist

Verifiable memory and decision lineage for high-stakes AI workflows.

CORTEX Persist is best understood as a trust layer for facts and decisions:

- Store structured facts and decisions.
- Hash-chain every write into a tamper-evident ledger.
- Search and recall persisted knowledge.
- Export evidence instead of reconstructing events later.

It fits alongside your existing stack. Use it with your current database, observability tooling,
and vector search where that makes sense.

## Start Here

- [Public Product Surface](product-surface.md) — the recommended boundary for product adoption
- [Course Suite](course/README.md) — GitHub-first tracks in English, Spanish, and Chinese
- [Quickstart](quickstart.md) — the shortest path from install to verified write
- [Installation](installation.md) — package extras and source installs
- [CLI Reference](cli.md) — recommended command surface
- [REST API Reference](api.md) — core HTTP endpoints first, advanced routes second
- [MCP Server](mcp.md) — IDE and agent integration via MCP
- Agent Taxonomy — roles vs builtins vs YAML agents
- [Skill Taxonomy](skills/SKILL-TAXONOMY.md) — skill manifests, routing, and the Antigravity-CORTEX nexus

## Product Fit

Use CORTEX Persist when you need:

- Evidence for decisions that matter after the fact.
- Traceable state transitions in long-running agent systems.
- Tamper detection on persisted memory.
- A local-first trust layer that does not force a new vector stack.

Do not treat it as a replacement for:

- Observability platforms such as Datadog or ELK.
- Dedicated vector databases for broad ephemeral retrieval.
- Human review, legal review, or compliance judgment.

## Recommended Adoption Path

```bash
pip install cortex-persist
cortex init
cortex store demo "We chose FastAPI over Flask for async support" --type decision
cortex search "async web framework"
cortex verify 1
cortex trust-ledger verify
```

If you need remote access next:

- Install the API extra for HTTP integrations: `pip install "cortex-persist[api]"`
- Install the MCP extra for IDE/agent integrations: `pip install "cortex-persist[mcp]"`

## Docs Map

| Section | Purpose |
| :--- | :--- |
| [Quickstart](quickstart.md) | Core workflow in a few commands |
| [Course Suite](course/README.md) | Multilingual tracks for swarms, optimization, and persistent memory |
| [Installation](installation.md) | Packaging, extras, and source installs |
| [Architecture](architecture.md) | Deeper system design |
| Agent Taxonomy | Governance roles, builtins, YAML definitions, and runtime instances |
| [Skill Taxonomy](skills/SKILL-TAXONOMY.md) | Skill manifests, routing, categories, and the Antigravity-CORTEX nexus |
| [Security Trust Model](SECURITY_TRUST_MODEL.md) | Guarantees and non-guarantees |
| [Compliance](compliance.md) | EU AI Act mapping and evidence posture |
| [Developer Guide](developer-guide.md) | Contributing and extending the repo |

## Boundary Note

The repository also ships broader operator and research surfaces: swarm orchestration, ask/stream
routes, dashboards, advanced scripts, and historical architecture documents. Those pieces remain
available, but the public product story prioritizes the verifiable-memory surface first.

*by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
