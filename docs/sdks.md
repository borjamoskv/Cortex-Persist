# SDKs

CORTEX provides official SDKs for Python and JavaScript/TypeScript.

The recommended first integration surface is the in-process Python engine. The JavaScript /
TypeScript SDK is an early HTTP client layer and depends on the REST API being available.

---

## Python SDK

The Python SDK is the primary interface, distributed as `cortex-persist` on PyPI.

### Install

```bash
pip install cortex-persist
```

If another process needs remote access instead of in-process embedding/search, host the API with:

```bash
pip install "cortex-persist[api]"
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

### Basic Usage

```python
from cortex import CortexEngine

# Synchronous usage
engine = CortexEngine(db_path="~/.cortex/cortex.db", auto_embed=True)
engine.init_db_sync()

# Store
fact_id = engine.store_sync("my-project", "Python is great", fact_type="knowledge")

# Search
results = engine.search_sync("programming languages", top_k=5)

# Recall all facts for a project
facts = engine.recall_sync("my-project")
```

### Async Usage

```python
from cortex import CortexEngine

async with CortexEngine() as engine:
    fact_id = await engine.store(
        project="my-agent",
        content="User prefers dark mode",
        fact_type="knowledge",
        tags=["ui", "preferences"],
    )

    results = await engine.search("user interface preferences")
    facts = await engine.recall("my-agent")
```

### Tenant-Scoped Usage

```python
from cortex import CortexEngine

async with CortexEngine() as engine:
    await engine.store(
        content="Approved loan #443",
        fact_type="decision",
        project="fintech-agent",
    )
```

### Consensus

```python
from cortex import CortexEngine

async with CortexEngine() as engine:
    await engine.vote_v2(
        fact_id=42,
        agent_id="agent:claude",
        value=1,  # 1 = verify, 0 = abstain/remove, -1 = dispute
    )
```

### Available Methods

| Method (Sync) | Method (Async) | Description |
|:---|:---|:---|
| `store_sync()` | `store()` | Store a fact |
| — | `store_many()` | Batch store |
| `search_sync()` | `search()` | Semantic search |
| `recall_sync()` | `recall()` | Get all project facts |
| — | `history()` | Temporal query |
| — | `deprecate()` | Soft-delete a fact |
| — | `update()` | Update a fact |
| — | `vote_v2()` | Cast reputation-weighted consensus vote |
| — | `retrieve()` | Get single fact by ID |
| — | `time_travel()` | Reconstruct state at timestamp |
| — | `find_path()` | Knowledge graph path finding |
| — | `stats()` | System statistics |
| `init_db_sync()` | `init_db()` | Initialize database |
| `export_snapshot()` | — | Export markdown snapshot helper |

---

## JavaScript / TypeScript SDK

> **Status:** Early development. Available at `sdks/js/`.

This SDK is not the canonical first path for adoption. Use it when you specifically want a remote
HTTP client instead of the local Python engine.

### Install (from source)

```bash
cd sdks/js
npm install
```

### Usage

```typescript
import { CortexClient } from '@cortex-persist/sdk';

const cortex = new CortexClient({
  baseUrl: 'http://localhost:8484',
  apiKey: 'ctx_your_api_key',
});

// Store a fact
const result = await cortex.store({
  project: 'my-app',
  content: 'User prefers dark mode',
  factType: 'knowledge',
});

// Search
const facts = await cortex.search({
  query: 'user preferences',
  topK: 5,
});

// Recall
const allFacts = await cortex.recall('my-app');
```

### Planned: npm Package

```bash
# Coming Q2 2026
npm install @cortex-persist/sdk
```

---

## REST API

Both SDKs communicate with the CORTEX REST API. You can also use the API directly with any HTTP client:

```bash
# cURL
curl -X POST http://localhost:8484/v1/facts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ctx_your_key" \
  -d '{"project": "demo", "content": "Hello from cURL", "fact_type": "knowledge"}'
```

See the [REST API Reference](api.md) for all endpoints.

See `examples/curl_cheatsheet.md` for more cURL examples and `examples/postman_collection.json` for Postman.
