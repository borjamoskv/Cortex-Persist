<!-- [C5-REAL] Exergy-Maximized -->
# Deployment

CORTEX supports multiple deployment models — from a single `pip install` to the included
Dockerfile. Kubernetes, compose, and sovereign-cloud blueprints are target-state deployment
patterns unless the corresponding files are present in this repository snapshot.

This page covers deployment shapes across the broader repository. The recommended adoption path is
still local verifiable memory first, then optional HTTP and MCP surfaces only when you need them.

---

## Local (Development)

The simplest deployment. Zero network dependencies.

```bash
pip install cortex-persist

# Add only the surfaces you need locally
pip install "cortex-persist[api]"
pip install "cortex-persist[mcp]"
cortex init

# Start REST API
uvicorn cortex.api:app --reload --port 8484

# Start MCP server (for IDE integration)
python -m cortex.mcp
```

Data lives in `~/.cortex/cortex.db` (SQLite).

If you only need the in-process engine or CLI, the base package is enough and you do not need to
run either service.

---

## Docker

### Development

```bash
docker build -t cortex-persist:local .
docker run --rm -p 8484:8484 cortex-persist:local
```

This repository snapshot ships a `Dockerfile`, but does not include `docker-compose.yml` or
`docker-compose.prod.yml`.

### Production

Use a compose file only after adding one for your environment. A production-oriented compose stack
typically includes:

- **Caddy** as TLS reverse proxy with automatic HTTPS
- Security headers (HSTS, X-Frame-Options, CSP)
- Health checks and restart policies

```yaml
# Example docker-compose.prod.yml excerpt; create this file in your deployment repo if needed.
services:
  cortex:
    build: .
    restart: unless-stopped
    environment:
      - CORTEX_DB=/data/cortex.db
    volumes:
      - cortex-data:/data

  caddy:
    image: caddy:latest
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
```

### Dockerfile

The included `Dockerfile` is API-oriented. Add the `mcp` extra only if you plan to host MCP from
the same image.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install ".[api]"
CMD ["uvicorn", "cortex.api:app", "--host", "0.0.0.0", "--port", "8484"]
```

---

## Kubernetes (Helm)

> **Coming Q2 2026.** Helm chart for production K8s deployment.

Planned architecture:

```
┌─────────────────────────────────────────────┐
│                 Ingress (TLS)               │
├─────────────────────────────────────────────┤
│          CORTEX API (Deployment)            │
│          replicas: 3                        │
├─────────────────────────────────────────────┤
│  Redis (L1)  │  Qdrant (L2)  │  AlloyDB (L3) │
└─────────────────────────────────────────────┘
```

---

## GCP Sovereign Cloud

> **Coming Q3 2026.** Production-grade GCP deployment blueprints.

Target architecture:

| Layer | Service | Purpose |
|:---|:---|:---|
| **L1** (Working) | Cloud Memorystore (Redis) | Sliding window working memory |
| **L2** (Vector) | Qdrant Cloud | 384-dim semantic search |
| **L3** (Ledger) | AlloyDB PostgreSQL | Hash-chained tamper-evident ledger |
| **API** | Cloud Run | Auto-scaling stateless API |
| **Orchestration** | GKE | Daemon and background services |

---

## Daemon Installation

CORTEX includes a self-healing background daemon that monitors 13 specialized areas.
The daemon is exposed as the `moskv-daemon` console script, not as a default `cortex daemon`
subcommand.

### macOS

```bash
moskv-daemon install
# Creates ~/Library/LaunchAgents/com.moskv.cortex-daemon.plist
# Auto-starts on login
```

### Linux

```bash
moskv-daemon install
# Creates ~/.config/systemd/user/cortex-daemon.service
# Enables and starts via systemd --user
```

### Windows

```bash
moskv-daemon install
# Creates Task Scheduler job triggered at logon
```

### Manual Control

```bash
moskv-daemon start       # Run in foreground
moskv-daemon status      # Show last check results
moskv-daemon uninstall   # Remove installed service
```

---

## Environment Variables

All settings are loaded from environment variables via `cortex/config.py`.

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_DB` | `~/.cortex/cortex.db` | Database path |
| `CORTEX_ALLOWED_ORIGINS` | `localhost:3000,5173` | CORS origins |
| `CORTEX_RATE_LIMIT` | `300` | Requests per window |
| `CORTEX_RATE_WINDOW` | `60` | Window in seconds |
| `CORTEX_EMBEDDINGS` | `local` | `local` or `api` |
| `CORTEX_EMBEDDINGS_PROVIDER` | `gemini` | API provider when `api` mode |
| `CORTEX_STORAGE` | `local` | `local`, `turso`, or `postgres` (default bootstrap remains local-first) |
| `POSTGRES_DSN` | — | PostgreSQL DSN when `CORTEX_STORAGE=postgres` |
| `CORTEX_PG_URL` | — | Alternate PostgreSQL DSN env var when `CORTEX_STORAGE=postgres` |
| `CORTEX_POOL_SIZE` | `5` | Connection pool size |
| `CORTEX_API_PORT` | `8484` | API server port |
| `TURSO_DATABASE_URL` | — | Turso edge DB URL |
| `TURSO_AUTH_TOKEN` | — | Turso auth token |
| `NEO4J_URI` | — | Neo4j connection URI |
| `NEO4J_USER` | — | Neo4j username |
| `NEO4J_PASSWORD` | — | Neo4j password |
| `STRIPE_SECRET_KEY` | — | Stripe billing key |
| `STRIPE_WEBHOOK_SECRET` | — | Stripe webhook signing |
| `CORTEX_ENABLE_EXPERIMENTAL_API` | `0` | Mount experimental HTTP surfaces such as `/gateway/*` |
| `CORTEX_ENABLE_EXPERIMENTAL_MCP` | `0` | Enable non-core MCP tool families and runtime integrations |
| `CORTEX_TELEGRAM_TOKEN` | — | Telegram bot token for notifications and webhook replies |
| `CORTEX_TELEGRAM_CHAT_ID` | — | Optional Telegram webhook allowlist / notification target |
| `CORTEX_TELEGRAM_WEBHOOK_SECRET` | — | Required secret for `/gateway/telegram/webhook` |

Call `config.reload()` to refresh at runtime (useful for test isolation).

See `.env.example` for the complete list with descriptions.

---

## Health Checks

- **HTTP**: `GET /health` → compact JSON with `status`, `engine`, and `health_index`
- **Metrics**: `GET /metrics` → Prometheus format
- **CLI**: `cortex status` → Full system diagnostic
- **Daemon**: `moskv-daemon status` → Monitor health

## Experimental Gateway Exposure

If you expose the gateway adapters over HTTP, enable the experimental router explicitly:

```bash
export CORTEX_ENABLE_EXPERIMENTAL_API=1
export CORTEX_TELEGRAM_WEBHOOK_SECRET="replace-me"
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Notes:

- `/gateway/v1/*` and `/gateway/telegram/webhook` are not mounted on the default core API surface.
- The Telegram webhook rejects requests when `CORTEX_TELEGRAM_WEBHOOK_SECRET` is unset.
- Set `CORTEX_TELEGRAM_CHAT_ID` if you want the webhook restricted to a single chat.

## Experimental MCP Exposure

If you need the broader MCP surface beyond the four core tools, enable it explicitly:

```bash
export CORTEX_ENABLE_EXPERIMENTAL_MCP=1
python -m cortex.mcp.server
```

Notes:

- Without the flag, the default MCP server exposes only `cortex_store`, `cortex_search`,
  `cortex_status`, and `cortex_ledger_verify`.
- Runtime daemons and operator MCP families are not started on the default core path.

---

## Backup

### SQLite Backup

```bash
# Simple copy (safe with WAL mode)
cp ~/.cortex/cortex.db ~/.cortex/cortex.db.bak

# Or use the Python engine snapshot helper
python - <<'PY'
from cortex import CortexEngine

engine = CortexEngine()
engine.export_snapshot("./snapshot.md")
PY
```

### Production Backup

For AlloyDB/PostgreSQL backends, use standard database backup tools (`pg_dump`, AlloyDB automated backups).

---

## Monitoring

CORTEX exposes Prometheus-compatible metrics at `/metrics`:

- `cortex_facts_total` — Total facts stored
- `cortex_search_latency_p50` / `p95` / `p99` — Search latencies
- `cortex_consensus_votes_total` — Consensus activity
- `cortex_daemon_health` — Background service status
- `cortex_db_size_bytes` — Database size

Integrate with Grafana, Datadog, or any Prometheus-compatible monitoring system.
