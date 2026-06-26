<!-- [C5-REAL] Exergy-Maximized -->
# Configuration Reference

All CORTEX settings are loaded from environment variables at import time via `cortex/config.py`. Call `config.reload()` to refresh at runtime.

Most adopters only need the local database path plus optional `api` or `mcp`
extras. The rest of this page includes broader runtime and operator settings;
the recommended public boundary remains the one described in
[Public Product Surface](product-surface.md).

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

When set to `local`, CORTEX uses `all-MiniLM-L6-v2` via ONNX Runtime for fast
local vector generation with no network calls.

---

## Storage Backends

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_STORAGE` | `local` | Storage backend: `local` (SQLite), `turso` (edge), or `postgres` |
| `TURSO_DATABASE_URL` | — | Turso edge database URL |
| `TURSO_AUTH_TOKEN` | — | Turso authentication token |
| `POSTGRES_DSN` | — | PostgreSQL DSN for `CORTEX_STORAGE=postgres` |
| `CORTEX_PG_URL` | — | Alternate PostgreSQL DSN env var for `CORTEX_STORAGE=postgres` |

The recommended core CLI/API bootstrap remains local-first. Broader storage
backends are advanced deployment options and some default HTTP surfaces still
assume `local`.

---

## Knowledge Graph

The current core configuration treats the graph backend as SQLite-based. The
recommended public surface does not expose a supported Neo4j configuration path.

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
| `CORTEX_LLM_PROVIDER` | — | Optional provider for `/v1/ask` and related LLM routes; set explicitly in deployment (examples: `deepseek`, `qwen`, `openai`, `anthropic`, `gemini`, `ollama`, `openrouter`, `custom`) |
| `CORTEX_LLM_MODEL` | `deepseek-v4` | Optional model override for the selected provider |
| `CORTEX_LLM_BASE_URL` | — | Base URL for `custom` or self-hosted OpenAI-compatible endpoints |
| `CORTEX_LLM_API_KEY` | — | Generic API key env var used by some runtime paths |

If no provider is configured for the active process, the `/v1/ask` endpoint
returns `503 Service Unavailable`. Provider-specific API keys may also be
required depending on the adapter you choose.

---

## Notification Bus

| Variable | Default | Description |
|:---|:---|:---|
| `CORTEX_TELEGRAM_TOKEN` | — | Telegram bot token for notifications and webhook replies |
| `CORTEX_TELEGRAM_CHAT_ID` | — | Optional Telegram chat allowlist for the webhook and default target for notifications |
| `CORTEX_TELEGRAM_WEBHOOK_SECRET` | — | Required secret token for `/gateway/telegram/webhook` |
| `CORTEX_NOTIFY_MIN_SEVERITY` | `warning` | Minimum notification severity delivered to adapters |

Falls back to OS-native notifications (macOS/Linux/Windows) if Telegram is not configured.

### Experimental Gateway

The REST and Telegram gateway adapters live behind the experimental API surface.
Set `CORTEX_ENABLE_EXPERIMENTAL_API=1` before starting FastAPI if you want these routes mounted.

- REST gateway: `/gateway/v1/*`
- Telegram webhook: `/gateway/telegram/webhook`

Telegram webhook contract:

- `CORTEX_TELEGRAM_WEBHOOK_SECRET` is required; the webhook fails closed with `503` if unset.
- `CORTEX_TELEGRAM_CHAT_ID` is optional; when set, only that chat ID is accepted.
- `CORTEX_TELEGRAM_TOKEN` is only required for outbound replies/notifications, not for parsing inbound webhook payloads.

### Experimental MCP

The extended MCP families live behind a separate gate.

- `CORTEX_ENABLE_EXPERIMENTAL_MCP=1` enables non-core MCP tools such as trace, trust/compliance,
  health, and operator/runtime integrations.
- Without that flag, the default MCP server exposes only the core toolset:
  `cortex_store`, `cortex_search`, `cortex_status`, and `cortex_ledger_verify`.

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
