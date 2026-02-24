# SDKs

CORTEX provides official SDKs for Python and JavaScript/TypeScript.

---

## Python SDK

The Python SDK is the primary interface, distributed as `cortex-memory` on PyPI.

### Install

```bash
pip install cortex-memory
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

### Multi-Tenant Usage

```python
engine = CortexEngine()

# Store with tenant isolation
await engine.store_fact(
    content="Approved loan #443",
    fact_type="decision",
    project="fintech-agent",
    tenant_id="enterprise-customer-a",
)
```

### Consensus

```python
# Register an agent
# Agents are auto-registered on first vote

# Cast a vote
await engine.vote(
    fact_id=42,
    agent_id="agent:claude",
    vote=1,  # 1 = verify, -1 = dispute
)
```

### Available Methods

| Method (Sync) | Method (Async) | Description |
|:---|:---|:---|
| `store_sync()` | `store()` | Store a fact |
| `store_many_sync()` | `store_many()` | Batch store |
| `search_sync()` | `search()` | Semantic search |
| `recall_sync()` | `recall()` | Get all project facts |
| `history_sync()` | `history()` | Temporal query |
| `deprecate_sync()` | `deprecate()` | Soft-delete a fact |
| `update_sync()` | `update()` | Update a fact |
| `vote_sync()` | `vote()` | Cast consensus vote |
| `retrieve()` | `retrieve()` | Get single fact by ID |
| `time_travel()` | `time_travel()` | Reconstruct state at timestamp |
| `find_path()` | `find_path()` | Knowledge graph path finding |
| `stats()` | `stats()` | System statistics |
| `init_db_sync()` | `init_db()` | Initialize database |
| `export_snapshot()` | `export_snapshot()` | Export markdown snapshot |

---

## JavaScript / TypeScript SDK

> **Status:** Early development. Available at `sdks/js/`.

### Install (from source)

```bash
cd sdks/js
npm install
```

### Usage

```typescript
import { CortexClient } from '@cortex-memory/sdk';

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
npm install @cortex-memory/sdk
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
