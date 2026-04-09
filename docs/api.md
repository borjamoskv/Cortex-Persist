# CORTEX Persist API Reference

This page describes the repo-versioned API surface that is safe to advertise today.
The primary onboarding path remains the local-first CLI core in [Supported Core](supported-core.md) and [Canonical Demo](canonical-demo.md). The API is an optional self-hosted beta surface from the same source checkout.

## Startup

Install the API extras and run the FastAPI app locally:

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install -e ".[api]"
uvicorn cortex.api:app --port 8000
```

Health check:

```bash
curl http://localhost:8000/v1/status
```

## Authentication

- API keys can be passed with `Authorization: Bearer <key>`.
- For the Python client, `CORTEX_API_KEY` can be used as the default environment variable.
- Admin endpoints should remain restricted to trusted operators.

## Beta API Endpoints

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/v1/status` | Engine health and status summary |
| `POST` | `/v1/facts` | Store a fact |
| `POST` | `/v1/search` | Semantic search |
| `GET` | `/v1/projects/{project}/facts` | Recall facts for a project |
| `DELETE` | `/v1/facts/{fact_id}` | Deprecate a fact |
| `POST` | `/v1/admin/keys` | Create an API key |
| `GET` | `/v1/admin/keys` | List API keys |

## Python Client

The packaged public import surface is aligned with the distribution name:

```python
from cortex_persist import CortexClient

client = CortexClient("http://localhost:8000", api_key="ctx_example")
fact_id = client.store("demo", "CORTEX stores verifiable facts")
results = client.search("verifiable facts", k=3, project="demo")
status = client.status()
client.close()
```

## CLI Parity

The currently supported public product core maps cleanly to the CLI:

- `cortex init`
- `cortex store`
- `cortex recall`
- `cortex search`
- `cortex verify`
- `cortex trust-ledger verify --full`
- `cortex export`

## Related References

- [Supported Core](supported-core.md)
- [Canonical Demo](canonical-demo.md)
- [Operations](OPERATIONS.md)
- [Security & Trust Model](SECURITY_TRUST_MODEL.md)
- [examples/quickstart.py on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/examples/quickstart.py)
- [Python SDK README on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/sdks/python/README.md)
