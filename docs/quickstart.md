# Quickstart

Get CORTEX running in 5 minutes.

---

## 1. Install

```bash
pip install cortex-memory
```

For the API server and MCP:

```bash
pip install cortex-memory[api]
```

---

## 2. Initialize

```bash
cortex init
```

This creates `~/.cortex/cortex.db` with the full schema — facts, transactions, embeddings, consensus tables, and more.

---

## 3. Store Facts

Every fact is automatically hash-chained into an immutable ledger.

```bash
# Store knowledge
cortex store my-project "Redis uses skip lists for sorted sets" --tags "redis,data-structures"

# Store a decision (with automatic provenance detection)
cortex store my-project "We chose FastAPI over Flask for async support" --type decision

# Store an error pattern
cortex store my-project "OOM when batch size > 1024 on 8GB RAM" --type error

# Store with explicit source
cortex store my-project "Rate limit is 100 req/min" --type config --source "agent:gpt-4"
```

---

## 4. Verify Integrity

```bash
# Verify a single fact's cryptographic chain
cortex verify 1
# → ✅ VERIFIED — Hash chain intact

# Verify the entire ledger
cortex ledger verify
# → ✅ All 42 transactions verified. Chain is intact.

# Generate a compliance report
cortex compliance-report
# → Compliance Score: 5/5 — All Article 12 requirements met
```

---

## 5. Search

Semantic search finds conceptually similar facts using embedded vectors:

```bash
cortex search "how are sorted sets implemented?"

# Scope to a specific project
cortex search "async web framework" --project my-project

# Limit results
cortex search "database optimization" -k 3
```

---

## 6. Recall

Load all active facts for a project:

```bash
cortex recall my-project
```

---

## 7. Time Travel

Query what you knew at a specific point in time:

```bash
cortex history my-project --at "2026-01-15T10:00:00"
```

---

## 8. Multi-Agent Consensus

Multiple agents can verify or dispute facts:

```bash
# An agent votes to verify a fact
cortex vote 42 --agent "agent:claude" --vote verify

# Another agent disputes it
cortex vote 42 --agent "agent:gpt-4" --vote dispute
```

The consensus score is automatically updated based on agent reputation weights.

---

## 9. Run as MCP Server

CORTEX speaks the **Model Context Protocol**, making it a plug-in for any compatible AI IDE:

```bash
python -m cortex.mcp
```

Compatible with: **Claude Code**, **Cursor**, **OpenClaw**, **Windsurf**, **Antigravity**

Available MCP tools:

| Tool | Description |
|:---|:---|
| `cortex_store` | Store facts with automatic hash chaining |
| `cortex_search` | Hybrid semantic search |
| `cortex_status` | System health and metrics |
| `cortex_ledger_verify` | Full ledger integrity check |
| `cortex_audit_trail` | EU AI Act compliant audit log |
| `cortex_verify_fact` | Cryptographic verification certificate |
| `cortex_compliance_report` | Article 12 compliance snapshot |
| `cortex_decision_lineage` | Trace decision chains |

---

## 10. Run as REST API

```bash
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Then use the API:

```bash
# Store via API
curl -X POST http://localhost:8484/v1/facts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "project": "demo",
    "content": "CORTEX is running",
    "fact_type": "knowledge"
  }'

# Search via API
curl -X POST http://localhost:8484/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "cortex", "top_k": 5}'

# Interactive API docs
open http://localhost:8484/docs
```

---

## 11. Python SDK

```python
from cortex import CortexEngine

engine = CortexEngine()

# Async context manager
async with engine:
    # Store a fact
    fact_id = await engine.store(
        project="my-agent",
        content="Approved loan application #443",
        fact_type="decision",
    )

    # Search
    results = await engine.search("loan approval")

    # Verify
    facts = await engine.recall("my-agent")
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

- **[CLI Reference](cli.md)** — All 38 commands documented
- **[REST API Reference](api.md)** — Versioned REST endpoints and models
- **[MCP Server](mcp.md)** — Deep dive into MCP integration
- **[Architecture](architecture.md)** — How CORTEX works under the hood
- **[EU AI Act Compliance](compliance.md)** — Full Article 12 mapping
