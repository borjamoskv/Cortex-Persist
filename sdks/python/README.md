# CORTEX Python SDK

> ⚠️ **Not yet published.** This is an **experimental** thin-client SDK for the CORTEX Persist REST API. It is not published on PyPI and is not the same as `pip install cortex-persist` (the local-first engine).
>
> For the local-first engine: `pip install cortex-persist` and `from cortex import CortexEngine`.

Thin, zero-dependency client for the [CORTEX Persist API](https://github.com/borjamoskv/Cortex-Persist).

## Install

```bash
pip install cortex-persist
```

## Usage

```python
from cortex_sdk import Cortex

ctx = Cortex("http://localhost:8000", api_key="sk-xxx")

# Store
fact_id = ctx.store("user prefers dark mode", tags=["preferences"])

# Search (semantic + Graph RAG)
results = ctx.search("what does the user prefer?", top_k=3)
for r in results:
    print(f"[{r.score:.2f}] {r.content}")

# Recall all facts for a project
facts = ctx.recall("myproject", limit=50)

# Verify ledger integrity
report = ctx.verify()
print(f"Ledger valid: {report.valid} ({report.tx_checked} tx checked)")

# Knowledge graph
graph = ctx.graph("myproject")

# Time-travel query
results = ctx.search("status", as_of="2026-01-15T00:00:00")
```

## API Reference

| Method | Description |
|---|---|
| `store(content, **opts)` | Store a fact → returns `fact_id` |
| `search(query, **opts)` | Semantic search → `list[Fact]` |
| `recall(project, limit)` | Recall all facts → `list[Fact]` |
| `deprecate(fact_id)` | Soft-delete a fact |
| `verify()` | Ledger integrity check → `LedgerReport` |
| `checkpoint()` | Create Merkle checkpoint |
| `graph(project, limit)` | Knowledge graph data |
| `vote(fact_id, value)` | Cast consensus vote |

## License

Apache-2.0
