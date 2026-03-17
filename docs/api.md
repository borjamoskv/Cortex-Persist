# REST API Reference (v5.1 Consolidated)

CORTEX exposes a versioned FastAPI-based REST API.

---

## Facts & Memory (`/v1/facts`)

<<<<<<< HEAD
The central domain for storing and retrieving sovereign knowledge.
=======
```bash
pip install cortex-persist[api]
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Interactive OpenAPI docs: `http://localhost:8484/docs`

Full OpenAPI spec: [`openapi.yaml`](https://github.com/borjamoskv/cortex/blob/main/openapi.yaml) (70.5 KB)

---

## Authentication

API keys are managed via the admin endpoint. Keys are SHA-256 hashed before storage and support RBAC with 4 roles.

```bash
# Bootstrap: create first key (no auth required)
curl -X POST "http://localhost:8484/v1/admin/keys?name=my-client&tenant_id=default"

# Subsequent requests use Bearer auth
curl -H "Authorization: Bearer ctx_xxxxxxxxxx" http://localhost:8484/v1/status
```

### RBAC Roles

| Role | Permissions |
|:---|:---|
| `SYSTEM` | Full access |
| `ADMIN` | `read`, `write`, `manage:keys`, `system:config` |
| `AGENT` | `read`, `write` |
| `VIEWER` | `read` only |

---

## Health & Monitoring

### `GET /health`

Simple status check for load balancers.

```json
{"status": "ok", "version": "8.0.0a1"}
```

### `GET /metrics`

Prometheus-compatible metrics (p50/p95/p99 latencies, fact counts, consensus stats).

### `GET /v1/status`

Engine statistics and health.

```json
{
  "version": "8.0.0a1",
  "db_path": "/Users/you/.cortex/cortex.db",
  "db_size_mb": 2.4,
  "total_facts": 150,
  "active_facts": 142,
  "deprecated_facts": 8,
  "project_count": 5,
  "embeddings": 142,
  "transactions": 158
}
```

---

## Facts
>>>>>>> origin/main

### `POST /v1/facts`
Store a single fact (scoped to tenant).
- **Body**: `StoreRequest` (project, content, fact_type, tags, source, meta)

### `POST /v1/facts/batch`
Store up to 100 facts in one call.
- **Body**: `BatchStoreRequest`

### `GET /v1/facts/{id}`
Retrieve a single fact by ID with full metadata and cryptographic hash.

### `GET /v1/projects/{project}/facts`
Paginated recall of facts for a specific project.

### `POST /v1/facts/search`
Semantic search across all tenant facts. Supports `as_of` temporal filtering.

### `DELETE /v1/facts/{id}`
Soft-deprecate a fact.

### `GET /v1/facts/verify`
Verify the cryptographic integrity of the entire memory ledger.

### `POST /v1/facts/{id}/taint`
[Ω₁₃] Trigger recursive confidence downgrades on suspected facts.

---

## Swarm & Worktrees (`/v1/swarm`)

Orchestration surface for isolated agent deployment (Hito 3).

### `GET /v1/swarm/status`
Global health metrics, active worktrees, and agent PIDs.

### `POST /v1/swarm/worktrees`
Provision an isolated git worktree environment.
- **Body**: `{"branch_name": "...", "base_path": "..."}`

### `GET /v1/swarm/worktrees/{id}`
Retrieve metadata for an active worktree.

### `DELETE /v1/swarm/worktrees/{id}`
Terminate and cleanup an isolated execution environment.

---

## Trust & Compliance (`/v1/trust`)

Sovereign guardrails and regulatory alignment.

### `POST /v1/trust/guard`
Check if a proposed action violates existing trust boundaries.

### `GET /v1/trust/compliance`
Retrieve EU AI Act or custom compliance status reports.

---

## Admin & Health

### `GET /v1/status`
Engine health, cortisol levels, and neuroplasticity metrics.

### `GET /health`
Standard service health.
