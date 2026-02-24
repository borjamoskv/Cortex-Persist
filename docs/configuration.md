# Configuration Reference

All CORTEX settings are loaded from environment variables at import time via `cortex/config.py`. Call `config.reload()` to refresh at runtime.

---

## Core

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_DB` | `~/.cortex/cortex.db` | Path to the SQLite database |
| `CORTEX_API_PORT` | `8484` | REST API server port |
| `CORTEX_POOL_SIZE` | `5` | Connection pool size for async operations |

---

## Security

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_ALLOWED_ORIGINS` | `localhost:3000,5173` | Comma-separated CORS origins |
| `CORTEX_RATE_LIMIT` | `300` | Max requests per rate window |
| `CORTEX_RATE_WINDOW` | `60` | Rate limit window in seconds |

---

## Embeddings

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_EMBEDDINGS` | `local` | Embedding mode: `local` (ONNX) or `api` |
| `CORTEX_EMBEDDINGS_PROVIDER` | `gemini` | API provider when in `api` mode: `gemini`, `openai` |
| `GOOGLE_API_KEY` | — | Google Gemini API key (for API embeddings) |
| `OPENAI_API_KEY` | — | OpenAI API key (for API embeddings) |

When set to `local`, CORTEX uses `all-MiniLM-L6-v2` via ONNX Runtime for sub-5ms vector generation. No network calls.

---

## Storage Backends

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_STORAGE` | `local` | Storage backend: `local` (SQLite) or `turso` (edge) |
| `TURSO_DATABASE_URL` | — | Turso edge database URL |
| `TURSO_AUTH_TOKEN` | — | Turso authentication token |

---

## Knowledge Graph

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_GRAPH_BACKEND` | `sqlite` | Graph backend: `sqlite` or `neo4j` |
| `NEO4J_URI` | — | Neo4j connection URI (e.g., `bolt://localhost:7687`) |
| `NEO4J_USER` | — | Neo4j username |
| `NEO4J_PASSWORD` | — | Neo4j password |

---

## Billing (SaaS)

| Variable | Default | Description |
|:---|:---|:---|
| `STRIPE_SECRET_KEY` | — | Stripe secret API key |
| `STRIPE_WEBHOOK_SECRET` | — | Stripe webhook signing secret |

---

## LLM Providers

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_LLM_PROVIDER` | — | LLM provider for `/v1/ask`: `gemini`, `openai`, `anthropic` |
| `GOOGLE_API_KEY` | — | Google Gemini API key |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |

If no provider is configured, the `/v1/ask` endpoint returns `503 Service Unavailable`.

---

## Notification Bus

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_TELEGRAM_BOT_TOKEN` | — | Telegram bot token for notifications |
| `CORTEX_TELEGRAM_CHAT_ID` | — | Telegram chat ID |

Falls back to OS-native notifications (macOS/Linux/Windows) if Telegram is not configured.

---

## Usage in Code

```python
from cortex import config

# Read a value
print(config.DB_PATH)
print(config.POOL_SIZE)

# After changing env vars, refresh:
config.reload()
```

!!! warning "Test Isolation"
    Always call `config.reload()` after patching environment variables in tests. The global `conftest.py` does this automatically via autouse fixtures.

---

## `.env.example`

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

The `.env` file is git-ignored by default.
