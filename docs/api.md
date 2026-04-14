# REST API Reference

CORTEX exposes a FastAPI application via `cortex.api:app`.

The default HTTP surface is intentionally narrow and centered on the verifiable-memory core:

- facts and recall
- semantic search
- ledger verification
- trust and compliance
- health and admin status

Broader orchestration surfaces still exist in the repo, but they are now opt-in and should be treated as experimental unless you explicitly enable them.

---

## Run Locally

```bash
pip install cortex-persist[api]
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Interactive docs: `http://localhost:8484/docs`

To export a static OpenAPI document:

```bash
python -c "from cortex.api.openapi import export_openapi_spec; print(export_openapi_spec())"
```

By default this writes `docs/openapi.json`.

## API Tiers

### Default Core Surface

The default app mounts only the stable product surface. This is the recommended mode for:

- local-first memory deployments
- audit-heavy workflows
- SDK consumers that need a predictable contract

### Experimental Surface

To opt into orchestration, swarm, realtime, dashboard, onboarding, and other non-core routes:

```bash
export CORTEX_ENABLE_EXPERIMENTAL_API=1
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Set the same environment variable before exporting OpenAPI if you want the wider schema.

---

## Authentication

API keys are created through the admin surface and then passed as Bearer tokens.

```bash
# Bootstrap the first key
curl -X POST "http://localhost:8484/v1/admin/keys?name=my-client&tenant_id=default"

# Use the returned token on subsequent requests
curl -H "Authorization: Bearer ctx_xxxxxxxxxx" \
  http://localhost:8484/v1/status
```

### RBAC Roles

| Role | Permissions |
| :--- | :--- |
| `SYSTEM` | Full access |
| `ADMIN` | Administrative and write operations |
| `AGENT` | Read and write operations |
| `VIEWER` | Read-only access |

---

## Core Endpoints

### Facts & Memory

- `POST /v1/facts` — Store a single fact for the authenticated tenant.
- `POST /v1/facts/batch` — Store up to 100 facts in one request.
- `GET /v1/facts` — List active facts across projects for the tenant.
- `GET /v1/facts/{fact_id}` — Retrieve one fact with metadata and hash.
- `GET /v1/projects/{project}/facts` — Recall facts for a specific project.
- `POST /v1/facts/search` — Semantic search with optional `project` and `as_of`.
- `GET /v1/facts/{fact_id}/history` — Retrieve the fact version/history chain.
- `GET /v1/facts/{fact_id}/chain` — Retrieve the causal chain for a fact.
- `GET /v1/facts/verify` — Verify ledger integrity across persisted facts.
- `POST /v1/facts/{fact_id}/vote` — Cast a consensus vote on a fact.
- `POST /v1/facts/{fact_id}/vote-v2` — Cast a reputation-weighted consensus vote.
- `GET /v1/facts/{fact_id}/votes` — List votes registered for a fact.
- `POST /v1/facts/{fact_id}/taint` — Trigger taint propagation from a suspect fact.
- `DELETE /v1/facts/{fact_id}` — Soft-deprecate a fact.

### Trust, Governance & Health

- `GET /health` — Lightweight service health endpoint.
- `GET /v1/status` — Engine status, counts, and database size.
- `GET /v1/health/deep` — Deep subsystem health probes.
- `POST /v1/admin/keys` — Create API keys.
- `GET /v1/admin/keys` — List API keys.
- `GET /v1/projects/{project}/export` — Export project facts as JSON.
- `POST /v1/trust/guard` — Dry-run a proposed write against the storage guard.
- `GET /v1/trust/profiles/{agent_id}` — Retrieve the trust profile for one agent.
- `GET /v1/trust/compliance` — Generate compliance status derived from live state.

## Experimental Endpoints

These routes are available only when `CORTEX_ENABLE_EXPERIMENTAL_API=1`:

- `GET /v1/swarm/status` — Aggregate swarm health and active worktrees.
- `POST /v1/swarm/worktrees` — Provision an isolated git worktree.
- `GET /v1/swarm/worktrees/{worktree_id}` — Inspect a provisioned worktree.
- `DELETE /v1/swarm/worktrees/{worktree_id}` — Tear down a worktree.
- `POST /v1/swarm/psychohistory` — Run a psychohistory simulation.
- `POST /v1/ask` and `POST /v1/ask/stream` — Retrieval + synthesis endpoints.
- `POST /v1/agents` and `GET /v1/agents...` — Agent registration and inspection.
- `GET /v1/context/*` — Context inference, signals, and history endpoints.
- `GET /v1/events/stream` — Coordination/event streaming.
- `GET /telemetry/*` and realtime topology/dashboard routes — operator-oriented observability surfaces.
- `GET /v1/runtime/*`, `/v1/usage/*`, `/v1/signup` and similar routes — supporting operational or growth surfaces.

---

## Compatibility Notes

Legacy clients using `/v1/memories/*` are redirected to `/v1/facts/*` for backward
compatibility. New integrations should target `/v1/facts`, `/v1/search`, `/v1/ledger`, and `/v1/trust` first.
