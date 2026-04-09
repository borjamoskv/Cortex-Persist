# CORTEX Python SDK

Thin client for the [CORTEX Persist API](https://github.com/borjamoskv/Cortex-Persist).

## Install

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install .
```

The standalone `cortex-persist-sdk` package is not published on PyPI yet. Use the
client shipped in the main repository package for now. The public import surface
for that package is `from cortex_persist import CortexClient`.

## Run The Beta API

`CortexClient` talks to the self-hosted beta API. Start that API from the same
repository checkout:

```bash
pip install -e ".[api]"
uvicorn cortex.api:app --port 8000
```

The CLI canonical demo remains the shortest path for the full trust proof,
including fact verification and export: [docs/canonical-demo.md](../../docs/canonical-demo.md).

## Usage

```python
from cortex_persist import CortexClient

ctx = CortexClient("http://localhost:8000", api_key="sk-xxx")

# Store
fact_id = ctx.store(
    project="myproject",
    content="user prefers dark mode",
    tags=["preferences"],
)

# Search
results = ctx.search("what does the user prefer?", k=3, project="myproject")
for r in results:
    print(f"[{r.score:.2f}] {r.content}")

# Recall all facts for a project
facts = ctx.recall("myproject")

# Engine status
status = ctx.status()
print(status)
```

## API Reference

| Method | Description |
|---|---|
| `store(project, content, fact_type="knowledge", tags=None, metadata=None)` | Store a fact → returns `fact_id` |
| `search(query, k=5, project=None)` | Semantic search → `list[Fact]` |
| `recall(project, include_deprecated=False)` | Recall all facts → `list[Fact]` |
| `deprecate(fact_id)` | Soft-delete a fact |
| `status()` | Engine status summary |
| `create_key(name, tenant_id="default")` | Create an API key |
| `list_keys()` | List API keys |

Verification and export remain CLI-first in the current supported product flow.

## License

Apache-2.0
