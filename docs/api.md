# REST API Reference

CORTEX exposes a versioned FastAPI-based REST API.

---

## Start the Server

```bash
pip install cortex-memory[api]
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

### `POST /v1/facts`

Store a fact (scoped to authenticated tenant).

**Request:**

```json
{
  "project": "my-project",
  "content": "Redis uses skip lists for sorted sets",
  "fact_type": "knowledge",
  "tags": ["redis", "data-structures"],
  "confidence": "stated",
  "source": "documentation"
}
```

**Response:**

```json
{
  "fact_id": 42,
  "project": "my-project",
  "tx_hash": "a1b2c3..."
}
```

### `GET /v1/projects/{project}/facts`

Recall facts for a project with tenant isolation.

| Parameter | Type | Description |
|:---|:---|:---|
| `project` | path | Project name |
| `limit` | query | Max results (1-1000) |

### `DELETE /v1/facts/{fact_id}`

Soft-deprecate a fact (mark as invalid). The fact remains in the ledger for audit purposes.

---

## Search

### `POST /v1/search`

Semantic + Graph-RAG search across facts (scoped to tenant).

**Request:**

```json
{
  "query": "sorted set implementation",
  "project": null,
  "top_k": 5,
  "as_of": null,
  "include_graph": false,
  "graph_depth": 0
}
```

**Response:**

```json
{
  "results": [
    {
      "fact_id": 42,
      "project": "my-project",
      "content": "Redis uses skip lists for sorted sets",
      "fact_type": "knowledge",
      "score": 0.89,
      "tags": ["redis", "data-structures"]
    }
  ]
}
```

### `GET /v1/search`

Same as POST, but via query parameters: `?query=...&k=5&as_of=...&include_graph=true`

---

## Ask (RAG)

### `POST /v1/ask`

RAG endpoint: search → synthesize → answer. Searches CORTEX memory for relevant facts, then uses the configured LLM to produce a grounded answer.

**Request:**

```json
{
  "question": "What database does our API use?",
  "project": "my-project",
  "top_k": 5
}
```

**Response:**

```json
{
  "answer": "Based on your project's memory, your API uses Redis...",
  "sources": [
    {"fact_id": 42, "content": "...", "score": 0.89}
  ]
}
```

Returns `503` if no LLM provider is configured.

### `GET /v1/llm/status`

Check which LLM provider is active and list supported providers.

---

## Consensus

### `POST /v1/facts/{fact_id}/vote`

Cast a consensus vote (verify/dispute) on a fact.

**Request:**

```json
{
  "agent_id": "agent:claude",
  "vote": 1,
  "domain": "general"
}
```

### `POST /v1/facts/{fact_id}/vote-v2`

Cast a reputation-weighted consensus vote (RWC).

### `GET /v1/facts/{fact_id}/votes`

Retrieve all votes for a specific fact.

---

## Time Tracking

### `POST /v1/heartbeat`

Record an activity heartbeat for automatic time tracking.

```json
{
  "project": "my-project",
  "entity": "src/main.py",
  "category": "coding",
  "branch": "feature/auth"
}
```

### `GET /v1/time/today`

Get today's time tracking summary (optional project filter).

### `GET /v1/time`

Get time tracking report for the last N days (`?days=7`).

### `GET /v1/time/history`

Get daily time history.

---

## Admin

### `POST /v1/admin/keys`

Create a new API key. First key requires no auth (bootstrap).

| Parameter | Type | Description |
|:---|:---|:---|
| `name` | query | Key name (required) |
| `tenant_id` | query | Tenant scope (default: `default`) |

### `GET /v1/admin/keys`

List all API keys (hashed — never reveals raw key).

### `POST /v1/handoff`

Generate a session handoff document with hot context.

### `GET /v1/projects/{project}/export`

Export a project to JSON (`?format=json`) or other formats.

---

## Knowledge Graph

### `POST /v1/graph`

Query the knowledge graph (entity-relation).

### `GET /v1/graph/patterns`

Get detected graph patterns.

---

## Security Middleware

All API responses include:

| Header | Value |
|:---|:---|
| `Content-Security-Policy` | `default-src 'self'` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `X-XSS-Protection` | `1; mode=block` |

Rate limiting: **300 requests per 60-second window** per IP (configurable).

Content size limit enforced to prevent DoS.

---

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error description"
}
```

| Status | Meaning |
|:---|:---|
| `200` | Success |
| `401` | Missing or invalid API key |
| `403` | Insufficient permissions |
| `404` | Resource not found |
| `422` | Validation error |
| `429` | Rate limit exceeded |
| `500` | Internal server error |
| `503` | Service unavailable (e.g., no LLM configured) |

---

## Multi-Tenant Usage

When using API keys with `tenant_id`, all operations are automatically scoped:

```bash
# Create a tenant-scoped key
curl -X POST "http://localhost:8484/v1/admin/keys?name=tenant-a&tenant_id=enterprise-a"

# All subsequent requests with this key only see tenant-a data
curl -H "Authorization: Bearer ctx_tenant_a_key" \
  http://localhost:8484/v1/search?query=hello
```

Tenants are cryptographically isolated at all memory layers (L1, L2, L3).
