# Public Product Surface

This document defines the recommended integration surface for CORTEX Persist.

The repository contains more than the core product: there are operator workflows, swarm tooling,
runtime endpoints, dashboards, and historical research artifacts. Those pieces can be useful, but
they are not the best first integration target and they evolve faster than the verifiable-memory
surface.

## Product Promise

For product adoption, treat CORTEX Persist primarily as:

- A verifiable memory layer for facts and decisions.
- A tamper-evident ledger with cryptographic verification.
- A search and recall layer over persisted facts.
- An evidence/export surface for audits, reviews, and incident response.

The default adoption path is:

1. Initialize a local ledger.
2. Store facts or decisions.
3. Search and recall them.
4. Verify integrity and generate evidence.
5. Add HTTP or MCP only when another process needs remote access.

## Core CLI Surface

These commands form the recommended CLI surface:

- `cortex init`
- `cortex store PROJECT CONTENT`
- `cortex search QUERY`
- `cortex recall PROJECT`
- `cortex history PROJECT --at ...`
- `cortex list`
- `cortex edit FACT_ID NEW_CONTENT`
- `cortex delete FACT_ID`
- `cortex status`
- `cortex verify FACT_ID`
- `cortex trust-ledger verify`
- `cortex compliance-report`

The root CLI exposes only this core surface by default. Operator and research commands remain
available behind `CORTEX_ENABLE_EXPERIMENTAL_CLI=1`, but they are not the public product baseline.

## Core Python Surface

The recommended programmatic entry point is `CortexEngine`:

- `store()`
- `search()`
- `recall()`
- `history()`
- `verify_ledger()`
- `stats()`

For most integrations, start here before adopting broader in-repo subsystems.

## Core HTTP Surface

The FastAPI app includes many routes. For product integrations, prefer this subset first:

- `GET /health`
- `GET /v1/status`
- `POST /v1/facts`
- `POST /v1/facts/batch`
- `GET /v1/facts`
- `GET /v1/facts/{fact_id}`
- `GET /v1/projects/{project}/facts`
- `POST /v1/facts/search`
- `GET /v1/facts/{fact_id}/history`
- `GET /v1/facts/{fact_id}/chain`
- `GET /v1/facts/verify`
- `DELETE /v1/facts/{fact_id}`
- `GET /v1/ledger/status`
- `GET /v1/ledger/verify`
- `POST /v1/ledger/checkpoint`
- `POST /v1/admin/keys`
- `GET /v1/admin/keys`
- `GET /v1/projects/{project}/export`
- `POST /v1/trust/guard`
- `GET /v1/trust/profiles/{agent_id}`
- `GET /v1/trust/compliance`

The same app also ships broader routes such as swarm orchestration, agents, ask/stream, context,
dashboard, onboarding, telemetry, and runtime helpers. Those are available in-repo, but they are
mounted only when `CORTEX_ENABLE_EXPERIMENTAL_API=1`.

## Core MCP Surface

For IDE and agent integrations, the recommended minimum toolset is:

- `cortex_store`
- `cortex_search`
- `cortex_status`
- `cortex_ledger_verify`

The MCP server also exposes additional trust, trace, embedding, health, genesis, and operator
tools when `CORTEX_ENABLE_EXPERIMENTAL_MCP=1`. They are useful once you need them, but they are
not required to adopt CORTEX Persist as a verifiable memory layer.

## Advanced In-Repo Surfaces

The following areas exist in the repository but sit outside the core product story:

- Swarm orchestration and isolated worktree control.
- Agent registration and ask/stream inference endpoints.
- Runtime, dashboard, onboarding, telemetry, and operator utilities.
- Script catalogs under [`scripts/`](../scripts/README.md).
- Historical architecture, research, and proposal documents under `docs/`.

These surfaces can still be valuable, but they should be adopted deliberately and not inferred as
the default product contract.

## Recommended Doc Map

- [Quickstart](quickstart.md)
- [Installation](installation.md)
- [CLI Reference](cli.md)
- [REST API Reference](api.md)
- [MCP Server](mcp.md)
- [Security & Trust Model](SECURITY_TRUST_MODEL.md)
