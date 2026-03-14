# Operations — CORTEX Persist

Package: cortex-persist v0.3.0b1 · Engine: v8
License: Apache-2.0 · Python: >=3.10

> Runtime, maintenance, and troubleshooting procedures.
>
> Related: [`AGENTS.md`](../AGENTS.md) · [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## Environment Variables

```bash
GEMINI_API_KEY           # Google Gemini API key (LLM operations)
CORTEX_DB_PATH           # Override DB location (default: ~/.cortex/cortex.db)
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
| `[dev]` | pytest, pytest-cov, pytest-asyncio, httpx, z3-solver | Development & testing |
| `[adk]` | google-adk | Google Agent Development Kit |
| `[toolbox]` | toolbox-core | Toolbox integration |
| `[billing]` | stripe | Payment processing |
| `[cloud]` | asyncpg, redis, qdrant-client | Distributed backends |
| `[all]` | All of the above | Full installation |

---

## Entry Points

```text
cortex        → cortex.cli:cli          # Main CLI
moskv-daemon  → cortex.daemon_cli:main  # Background daemon
cortex-adk    → cortex.adk.runner:main  # Google ADK runner
```

---

## Running the API

```bash
# Development
uvicorn cortex.api:app --reload

# Production
uvicorn cortex.api:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Running the Daemon

```bash
# Start the background daemon
moskv-daemon start

# Check daemon status
moskv-daemon status
```

The daemon runs 13 monitors including health checks, compaction scheduling, sync operations, and integrity verification.

---

## CLI Operations

```bash
# Store a fact
cortex store --type decision --source agent:gemini PROJECT "content"

# Search facts
cortex search "query" --limit 10

# Verify ledger integrity
cortex verify

# Export context snapshot
cortex export
```

---

## Database Migrations

```bash
# Migrations run automatically on startup.
# To run manually:
cortex migrate

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
cortex verify

# Full integrity audit
cortex audit
```

---

## Observability

| Component | Details |
| --- | --- |
| `telemetry/` | OpenTelemetry-compatible span tracing |
| `signals/` | Event bus for pub/sub, reactive signals |
| `notifications/` | macOS native notifications (Darwin-only) |
| `daemon/` | 13 monitors — scheduler, watchers, health |
| `hypervisor/` | Process supervision, crash recovery, watchdog |
| `timing/` | Performance timing, SLA tracking |

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `LedgerIntegrityError` | Hash chain broken | Run `cortex verify` to identify break point |
| Slow search | Missing embeddings | Run `cortex reindex` |
| Import errors | Missing optional deps | Install with `pip install -e ".[all]"` |
| Daemon crash loop | Stale PID file | Remove `~/.cortex/daemon.pid` |
| Encryption errors | Missing or rotated key | Check `CORTEX_ENCRYPTION_KEY` or keyring |

---
