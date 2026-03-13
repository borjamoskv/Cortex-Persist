# cortex-persist

> **Give your AI agent a brain that remembers.**

Persistent memory infrastructure for AI agents. Store, search, and verify memories with semantic search and cryptographic integrity.

## Install

```bash
pip install cortex-persist
```

## Quickstart

```python
from cortex_persist import CortexMemory

# Initialize with your API key
memory = CortexMemory(api_key="ctx_your_key_here")

# Store a memory
memory_id = memory.store(
    project="my-agent",
    content="User prefers dark mode and concise responses",
    tags=["preference", "ui"],
)

# Semantic search
results = memory.search("what does the user prefer?")
for r in results:
    print(f"[{r.score:.2f}] {r.content}")

# List all memories for a project
memories = memory.list("my-agent")

# Delete a memory
memory.delete(memory_id)

# Check usage
usage = memory.usage()
print(f"Calls used: {usage['calls_used']}/{usage['calls_limit']}")
```

## Async Usage

```python
from cortex_persist import AsyncCortexMemory

async with AsyncCortexMemory(api_key="ctx_...") as memory:
    await memory.store("my-agent", "Important fact")
    results = await memory.search("important")
```

## Features

- **Semantic Search** — Find memories by meaning, not just keywords
- **Cryptographic Integrity** — Every memory is hash-chain verified
- **Tenant Isolation** — Your data is completely isolated
- **Temporal Queries** — Search "as of" a specific point in time
- **Batch Operations** — Store up to 100 memories in one call
- **Usage Tracking** — Monitor your API consumption

## API Reference

### `CortexMemory(api_key, base_url)`

| Method | Description |
|---|---|
| `store(project, content, tags, type, metadata)` | Store a memory → `int` |
| `search(query, k, project)` | Semantic search → `list[Memory]` |
| `list(project, limit)` | List memories → `list[Memory]` |
| `get(memory_id)` | Get single memory → `Memory` |
| `delete(memory_id)` | Delete memory → `bool` |
| `batch_store(memories)` | Batch store → `dict` |
| `verify()` | Check ledger integrity → `dict` |
| `usage()` | Get API usage → `dict` |

## Plans

| Plan | Calls/month | Projects | Storage |
|---|---|---|---|
| **Free** | 1,000 | 1 | 10 MB |
| **Pro** ($29/mo) | 50,000 | 10 | 1 GB |
| **Team** ($99/mo) | 500,000 | Unlimited | Unlimited |

## Links

- **API Docs**: [docs.cortex.moskv.com](https://docs.cortex.moskv.com)
- **Dashboard**: [cortex.moskv.com](https://cortex.moskv.com)
- **Sign Up**: `POST https://cortex.moskv.com/v1/signup`

---

*Built by [MOSKV](https://moskv.com) · Apache-2.0*
