# Operations — CORTEX Persist

Package: cortex-persist v0.3.0b3 · Engine: v8
License: Apache-2.0 · Python: >=3.10

> Runtime, maintenance, and troubleshooting procedures.
>
> Related: [`AGENTS.md`](https://github.com/borjamoskv/Cortex-Persist/blob/main/AGENTS.md) · [`architecture.md`](architecture.md)

---

## Environment Variables

```bash
GEMINI_API_KEY           # Google Gemini API key (LLM operations)
CORTEX_DB                # Override DB location (default: ~/.cortex/cortex.db)
CORTEX_LOG_LEVEL         # DEBUG | INFO | WARNING | ERROR
CORTEX_ENCRYPTION_KEY    # AES-256 master key (auto-generated if missing)
HF_TOKEN                 # Hugging Face token (private embedding models)
STRIPE_SECRET_KEY        # Stripe billing (optional: [billing])
REDIS_URL                # Redis connection (optional: [cloud])
DATABASE_URL             # PostgreSQL/AlloyDB (optional: [cloud])
```

---

## Local Setup

```bash
# Install — editable with all optional deps
pip install -e ".[all]"

# Verify installation
cortex --help
```

### Optional Dependency Groups

| Extra | Installs | Purpose |
| --- | --- | --- |
| `[api]` | FastAPI, Uvicorn, httpx | REST API server |
| `[mcp]` | mcp | Model Context Protocol server |
| `[dev]` | pytest, pytest-cov, pytest-asyncio, httpx, z3-solver | Development & testing |
| `[adk]` | google-adk | Google Agent Development Kit |
| `[toolbox]` | toolbox-core | Toolbox integration |
| `[billing]` | stripe | Payment processing |
| `[cloud]` | asyncpg, redis, qdrant-client | Distributed backends |
| `[trends]` | pytrends, pandas | Trend analysis integrations |
| `[all]` | All of the above | Full installation |

---

## Entry Points

```text
cortex        → cortex.cli:cli          # Main CLI
moskv-daemon  → cortex.daemon_cli:main  # Background daemon
cortex-adk    → cortex.adk.runner:main  # Google ADK runner
cortex-mcp    → cortex.mcp.server:run_server
```

---

## Running the API

```bash
# Development
uvicorn cortex.api:app --reload

# Production
uvicorn cortex.api:app --host 0.0.0.0 --port 8484 --workers 4
```

---

## Running the Daemon

```bash
# Start the background daemon
moskv-daemon start

# Check daemon status
moskv-daemon status
```

The daemon runs the background monitor set provided under `cortex/extensions/daemon/`, including
health checks, compaction scheduling, sync operations, and integrity verification.

---

## CLI Operations

```bash
# Store a fact
cortex store --type decision --source agent:gemini PROJECT "content"

# Search facts
cortex search "query" --top 10

# Verify one fact and the ledger hash chain
cortex verify 1
cortex trust-ledger verify

# Export context snapshot through the experimental CLI surface
CORTEX_ENABLE_EXPERIMENTAL_CLI=1 cortex export --format snapshot --out ./snapshot.md
```

---

## Database Migrations

```bash
# Core schema setup runs through `cortex init`.
# Legacy v3.1 → v4.0 import is available only through the experimental CLI surface:
CORTEX_ENABLE_EXPERIMENTAL_CLI=1 cortex migrate --source ~/.agent/memory

# Migration files live in cortex/migrations/
# Never modify existing migration files — only add new ones.
```

---

## Backup & Restore

```bash
# The database is a single SQLite file.
# Default location: ~/.cortex/cortex.db

# Backup
cp ~/.cortex/cortex.db ~/.cortex/cortex.db.backup

# Restore
cp ~/.cortex/cortex.db.backup ~/.cortex/cortex.db
```

For AlloyDB/cloud deployments, use standard PostgreSQL backup procedures.

---

## Integrity Verification

```bash
# Verify ledger hash chain
cortex trust-ledger verify

# Audit trail / extended audits live behind the experimental CLI surface
CORTEX_ENABLE_EXPERIMENTAL_CLI=1 cortex audit
```

---

## Observability

| Component | Details |
| --- | --- |
| `cortex/telemetry/` | OpenTelemetry-compatible span tracing |
| `cortex/extensions/signals/` | Event bus for pub/sub, reactive signals |
| `cortex/extensions/notifications/` | macOS native notifications and Telegram adapters |
| `cortex/extensions/daemon/` | Scheduler, watchers, health, and sync monitors |
| `cortex/extensions/hypervisor/` | Process supervision, crash recovery, watchdog |
| `cortex/extensions/timing/` | Performance timing and developer time tracking |

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `LedgerIntegrityError` | Hash chain broken | Run `cortex trust-ledger verify`; use `cortex verify <fact-id>` for a specific fact |
| Slow search | Missing embeddings | Re-store affected facts or use the experimental embedding/reindex tooling for the affected surface |
| Import errors | Missing optional deps | Install with `pip install -e ".[all]"` |
| Daemon crash loop | Stale PID file | Remove `~/.cortex/daemon.pid` |
| Encryption errors | Missing or rotated key | Check `CORTEX_ENCRYPTION_KEY` or keyring |

---
