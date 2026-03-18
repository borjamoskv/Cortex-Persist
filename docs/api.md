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

### `GET /v1/facts/{id}/chain`
Retrieve the causal chain (ancestors/descendants) for a specific fact.

---

## Consensus & Voting

### `POST /v1/facts/{id}/vote`
Verify or dispute a fact.

### `POST /v1/facts/{id}/vote-v2`
Reputation-weighted consensus (RWC).

### `GET /v1/facts/{id}/votes`
List all votes cast on a fact.

---

## Search (Legacy/Global)

### `POST /v1/search`
Global semantic + Graph-RAG search. (Planned move to `/v1/facts/search` in v2.0).

---

## Time Tracking

### `POST /v1/heartbeat`
Auto-track activity.

### `GET /v1/time/today`
Today's summary.

---

## Admin & Trust

### `POST /v1/admin/keys`
API key management.

### `GET /v1/status`
Engine health, cortisol levels, and neuroplasticity metrics.

### `GET /health`
Standard service health.
