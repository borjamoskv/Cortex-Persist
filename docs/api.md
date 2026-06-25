<!-- [C5-REAL] Exergy-Maximized -->
# CORTEX REST API Reference (LEGION-10k)

CORTEX exposes a high-throughput, C5-REAL verified FastAPI application via `cortex.api:app`.

By default, the FastAPI app mounts the core verifiable-memory and trust surface described here.
Broader operator/runtime routes are gated behind `CORTEX_ENABLE_EXPERIMENTAL_API=1`.

Interactive docs are available at `/docs` when the app is not running in production mode.

This page tracks the HTTP routes registered in the current tree. Some subsystems remain
feature-gated or depend on optional extras, and maturity still varies by router.

---

## Run Locally

```bash
pip install "cortex-persist[api]"
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Interactive docs: `http://localhost:8484/docs`

The default core API bootstrap fails closed unless `CORTEX_STORAGE=local`.

To export a static OpenAPI document:

```bash
python -c "from legacy_research.api.openapi import export_openapi_spec; print(export_openapi_spec())"
```

By default this writes `docs/openapi.json`.

---

## Authentication

API keys are created through the admin surface and then passed as Bearer tokens.

```bash
# Bootstrap the first key
curl -X POST "http://localhost:8484/v1/admin/keys?name=my-client&tenant_id=default"

# Use the returned token on subsequent requests
curl -H "Authorization: Bearer ctx_xxxxxxxxxx" \
  http://localhost:8484/v1/status
```

### RBAC Roles

| Role | Permissions |
| :--- | :--- |
| `SYSTEM` | Full access |
| `ADMIN` | Administrative and write operations |
| `AGENT` | Read and write operations |
| `VIEWER` | Read-only access |

---

## Recommended Sovereign Endpoints

### Facts And Memory (C5-REAL Verified)

- `POST /v1/facts` — Store a single fact for the authenticated tenant.
- `POST /v1/facts/batch` — Store up to 100 facts in one request.
- `GET /v1/facts` — List active facts across projects for the tenant.
- `GET /v1/facts/{fact_id}` — Retrieve one fact with metadata and hash.
- `GET /v1/projects/{project}/facts` — Recall facts for a specific project.
- `POST /v1/facts/search` — Semantic search with optional `project` and `as_of`.
- `GET /v1/facts/{fact_id}/history` — Retrieve the fact version/history chain.
- `GET /v1/facts/{fact_id}/chain` — Retrieve the causal chain for a fact.
- `GET /v1/facts/verify` — Verify ledger integrity across persisted facts.
- `DELETE /v1/facts/{fact_id}` — Soft-deprecate a fact.

### Trust, Governance, And Swarm Health

- `GET /health` — Lightweight service health endpoint returning `status`, `engine`, and `health_index`.
- `GET /v1/status` — Engine status, counts, and database size.
- `POST /v1/admin/keys` — Create API keys.
- `GET /v1/admin/keys` — List API keys.
- `GET /v1/projects/{project}/export` — Create a server-side JSON export artifact and return its location.
- `POST /v1/trust/guard` — Dry-run a proposed write against the storage guard.
- `GET /v1/trust/profiles/{agent_id}` — Retrieve the trust profile for one agent.
- `GET /v1/trust/compliance` — Generate compliance status derived from live state.

### Ledger

- `GET /v1/ledger/status` — Ledger statistics and checkpoint status.
- `GET /v1/ledger/verify` — Full ledger verification report.
- `POST /v1/ledger/checkpoint` — Seal new transactions into a Merkle checkpoint.

---

## Additional In-Repo Surfaces

When `CORTEX_ENABLE_EXPERIMENTAL_API=1`, the same FastAPI app also exposes broader
operator/runtime routes such as:

- `GET /v1/swarm/status`
- `POST /v1/swarm/worktrees`
- `POST /v1/ask` and `POST /v1/ask/stream`
- `POST /v1/agents` and `GET /v1/agents...`
- `GET /v1/context/*`
- dashboard, onboarding, runtime, telemetry, and related helper routes

These routes are real and usable, but they are not mounted on the default core API surface.

### Experimental Gateway Endpoints

The gateway adapters are not part of the default recommended core API contract.
If you choose to mount them, treat them as experimental surfaces and enable them explicitly in
deployment/configuration.

- `POST /gateway/v1/store`
- `POST /gateway/v1/search`
- `POST /gateway/v1/recall`
- `GET /gateway/v1/status`
- `POST /gateway/v1/emit`
- `POST /gateway/telegram/webhook`

Operational notes:

- Enable the surface explicitly with `CORTEX_ENABLE_EXPERIMENTAL_API=1`.
- Telegram webhook requests must present `X-Telegram-Bot-Api-Secret-Token` matching `CORTEX_TELEGRAM_WEBHOOK_SECRET`.
- `CORTEX_TELEGRAM_CHAT_ID` is optional and acts as a single-chat allowlist when configured.

---

## Compatibility Notes

Legacy clients using `/v1/memories/*` are redirected to `/v1/facts/*` for backward compatibility.
New integrations should target the `/v1/facts` surface directly.
