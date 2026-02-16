# Quickstart

Get CORTEX running in 5 minutes.

## 1. Install

```bash
pip install cortex-memory
```

For API server support:

```bash
pip install cortex-memory[api]
```

## 2. Initialize

```bash
cortex init
```

This creates `~/.cortex/cortex.db` with the full schema.

## 3. Store Facts

```bash
# Store a knowledge fact
cortex store my-project "Redis uses skip lists for sorted sets" --tags "redis,data-structures"

# Store a decision
cortex store my-project "We chose FastAPI over Flask for async support" --type decision

# Store an error pattern
cortex store my-project "OOM when batch size > 1024 on 8GB RAM" --type error
```

## 4. Search

Semantic search finds conceptually similar facts:

```bash
cortex search "how are sorted sets implemented?"

# Scope to a specific project
cortex search "async web framework" --project my-project
```

## 5. Recall

Load all active facts for a project:

```bash
cortex recall my-project
```

## 6. Time Travel

Query what you knew at a specific point in time:

```bash
cortex history my-project --at "2026-01-15T10:00:00"
```

## 7. API Server (Optional)

```bash
uvicorn cortex.api:app --host 0.0.0.0 --port 8742
```

Then use the API:

```bash
# Store via API
curl -X POST http://localhost:8742/store \
  -H "Content-Type: application/json" \
  -d '{"project": "demo", "content": "CORTEX is running", "fact_type": "knowledge"}'

# Search via API
curl -X POST http://localhost:8742/search \
  -H "Content-Type: application/json" \
  -d '{"query": "cortex", "top_k": 5}'

# Dashboard
open http://localhost:8742/dashboard
```

## Next Steps

- **[CLI Reference](cli.md)** — All 15 commands documented
- **[API Reference](api.md)** — REST endpoints and models
- **[Architecture](architecture.md)** — How CORTEX works under the hood
