# REST API Reference (v5.1 Consolidated)

CORTEX exposes a versioned FastAPI-based REST API.

---

## Facts & Memory (`/v1/facts`)

The central domain for storing and retrieving sovereign knowledge.

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
