# Quickstart

Get CORTEX Persist running in a few minutes using the recommended product path.

---

## 1. Install

```bash
pip install cortex-persist
```

Optional extras:

```bash
pip install "cortex-persist[api]"   # REST API
pip install "cortex-persist[mcp]"   # MCP server
```

---

## 2. Initialize

```bash
cortex init
```

This creates `~/.cortex/cortex.db` and prepares the local ledger.

---

## 3. Store Facts

Every fact is automatically hash-chained into an immutable ledger.

```bash
# Store knowledge
cortex store my-project "Redis uses skip lists for sorted sets" --tags "redis,data-structures"

# Store a decision
cortex store my-project "We chose FastAPI over Flask for async support" --type decision

# Store an error pattern
cortex store my-project "OOM when batch size > 1024 on 8GB RAM" --type error
```

---

## 4. Search And Recall

```bash
# Semantic search
cortex search "how are sorted sets implemented?"

# Scope to a specific project
cortex search "async web framework" --project my-project

# Load all active facts for a project
cortex recall my-project
```

---

## 5. Verify Integrity

```bash
# Verify a single fact's cryptographic chain
cortex verify 1

# Verify the entire ledger
cortex trust-ledger verify

# Generate a compliance report
cortex compliance-report
```

---

## 6. Time Travel

```bash
cortex history my-project --at "2026-01-15T10:00:00"
```

---

## 7. Run As REST API

Install the API extra first:

```bash
pip install "cortex-persist[api]"
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Then use the core HTTP surface:

```bash
# Bootstrap the first key
curl -X POST "http://localhost:8484/v1/admin/keys?name=my-client&tenant_id=default"

# Store via API
curl -X POST http://localhost:8484/v1/facts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "project": "demo",
    "content": "CORTEX is running",
    "fact_type": "knowledge"
  }'
```

---

## 8. Run As MCP Server

Install the MCP extra first:

```bash
pip install "cortex-persist[mcp]"
python -m cortex.mcp
```

Recommended core MCP tools:

| Tool | Purpose |
| :--- | :--- |
| `cortex_store` | Store a fact with ledger integrity |
| `cortex_search` | Search persisted memory |
| `cortex_status` | Health and DB statistics |
| `cortex_ledger_verify` | Verify chain integrity |

---

## 9. Python Integration

```python
from cortex import CortexEngine

engine = CortexEngine()

# Async context manager
async with engine:
    fact_id = await engine.store(
        project="my-agent",
        content="Approved loan application #443",
        fact_type="decision",
    )

    results = await engine.search("loan approval")
    ledger = await engine.verify_ledger()
```

Or use the synchronous API:

```python
engine = CortexEngine(auto_embed=True)
engine.init_db_sync()

fact_id = engine.store_sync("my-project", "Hello world", fact_type="knowledge")
results = engine.search_sync("greeting")
```

---

## Next Steps

- [Public Product Surface](product-surface.md) — Recommended boundary for adoption
- [CLI Reference](cli.md) — Core commands first
- [REST API Reference](api.md) — Core HTTP surface first
- [MCP Server](mcp.md) — MCP install and tool surface
- [Architecture](architecture.md) — How CORTEX works under the hood
- [EU AI Act Compliance](compliance.md) — Full Article 12 mapping
