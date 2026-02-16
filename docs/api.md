# REST API Reference

CORTEX exposes a FastAPI-based REST API on port `8742`.

## Start the server

```bash
pip install cortex-memory[api]
uvicorn cortex.api:app --host 0.0.0.0 --port 8742
```

The interactive OpenAPI docs are available at `http://localhost:8742/docs`.

---

## Authentication

Some endpoints require an API key via the `X-API-Key` header. Keys are SHA-256 hashed before storage.

```bash
# Create a key via the API
curl -X POST http://localhost:8742/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-client", "permissions": ["read", "write"]}'
```

---

## Endpoints

### `POST /store`

Store a fact.

**Request body:**

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

---

### `POST /search`

Semantic search.

**Request body:**

```json
{
  "query": "sorted set implementation",
  "project": null,
  "top_k": 5,
  "as_of": null
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

---

### `GET /recall/{project}`

Load all active facts for a project.

**Response:**

```json
{
  "project": "my-project",
  "facts": [...],
  "count": 15
}
```

---

### `GET /status`

System health and statistics.

**Response:**

```json
{
  "version": "0.1.0",
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

### `GET /dashboard`

Embedded Industrial Noir dashboard with Chart.js visualizations.

---

### `POST /heartbeat`

Record an activity heartbeat for time tracking.

**Request body:**

```json
{
  "project": "my-project",
  "entity": "src/main.py",
  "category": "coding",
  "branch": "feature/auth"
}
```

---

### `GET /time`

Time tracking summary.

**Query parameters:**

| Parameter | Default | Description |
| --- | --- | --- |
| `project` | — | Filter by project |
| `days` | `1` | Number of days |

---

### `POST /deprecate/{fact_id}`

Soft-delete a fact.

**Query parameters:**

| Parameter | Description |
| --- | --- |
| `reason` | Reason for deprecation |

---

## Error Handling

| Status | Meaning |
| --- | --- |
| `200` | Success |
| `401` | Missing or invalid API key |
| `404` | Resource not found |
| `422` | Validation error (e.g., empty project name) |
| `500` | Internal server error |

All errors return:

```json
{
  "detail": "Error description"
}
```
