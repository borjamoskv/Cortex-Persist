# Deployment

CORTEX supports multiple deployment models — from a single `pip install` to production Kubernetes clusters.

---

## Local (Development)

The simplest deployment. Zero network dependencies.

```bash
pip install cortex-memory[api]
cortex init

# Start REST API
uvicorn cortex.api:app --reload --port 8484

# Start MCP server (for IDE integration)
python -m cortex.mcp
```

Data lives in `~/.cortex/cortex.db` (SQLite).

---

## Docker

### Development

```bash
docker compose up -d
```

The `docker-compose.yml` starts CORTEX with default settings.

### Production

```bash
docker compose -f docker-compose.prod.yml up -d
```

The production setup includes:

- **Caddy** as TLS reverse proxy with automatic HTTPS
- Security headers (HSTS, X-Frame-Options, CSP)
- Health checks and restart policies

```yaml
# docker-compose.prod.yml (excerpt)
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

The included `Dockerfile` uses a multi-stage build:

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
| **L3** (Ledger) | AlloyDB PostgreSQL | Hash-chained immutable ledger |
| **API** | Cloud Run | Auto-scaling stateless API |
| **Orchestration** | GKE | Daemon and background services |

---

## Daemon Installation

CORTEX includes a self-healing background daemon that monitors 13 specialized areas.

### macOS

```bash
cortex daemon install
# Creates ~/Library/LaunchAgents/com.moskv.cortex-daemon.plist
# Auto-starts on login
```

### Linux

```bash
cortex daemon install
# Creates ~/.config/systemd/user/cortex-daemon.service
# Enables and starts via systemd --user
```

### Windows

```bash
cortex daemon install
# Creates Task Scheduler job triggered at logon
```

### Manual Control

```bash
cortex daemon start     # Start
cortex daemon stop      # Stop
cortex daemon status    # Health check
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
| `CORTEX_STORAGE` | `local` | `local` or `turso` |
| `CORTEX_GRAPH_BACKEND` | `sqlite` | `sqlite` or `neo4j` |
| `CORTEX_POOL_SIZE` | `5` | Connection pool size |
| `CORTEX_API_PORT` | `8484` | API server port |
| `TURSO_DATABASE_URL` | — | Turso edge DB URL |
| `TURSO_AUTH_TOKEN` | — | Turso auth token |
| `NEO4J_URI` | — | Neo4j connection URI |
| `NEO4J_USER` | — | Neo4j username |
| `NEO4J_PASSWORD` | — | Neo4j password |
| `STRIPE_SECRET_KEY` | — | Stripe billing key |
| `STRIPE_WEBHOOK_SECRET` | — | Stripe webhook signing |

Call `config.reload()` to refresh at runtime (useful for test isolation).

See `.env.example` for the complete list with descriptions.

---

## Health Checks

- **HTTP**: `GET /health` → `{"status": "ok"}`
- **Metrics**: `GET /metrics` → Prometheus format
- **CLI**: `cortex status` → Full system diagnostic
- **Daemon**: `cortex daemon status` → Monitor health

---

## Backup

### SQLite Backup

```bash
# Simple copy (safe with WAL mode)
cp ~/.cortex/cortex.db ~/.cortex/cortex.db.bak

# Or use CORTEX snapshots
cortex export --out ./snapshot.md
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
