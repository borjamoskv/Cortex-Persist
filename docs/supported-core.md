# Supported Core

This page defines the minimum public contract that is safe to promise today.

If a command, import, endpoint, or deployment posture is not named here, treat it as beta, experimental, internal, or roadmap even if code exists elsewhere in the repository.

## Support Boundary

| Surface | Current Contract |
| :--- | :--- |
| Install path | Source install from this repository |
| Public Python import | `cortex_persist` |
| Supported operating posture | Local-first SQLite |
| API posture | Self-hosted from source, beta |
| Public package publication | Not yet part of the supported contract |

The repository still uses `cortex` as the internal runtime package for CLI, API, and MCP entrypoints. That implementation detail does not change the public import contract above.

## Local-First CLI Core

The current product core is CLI-first.

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install .
```

Supported commands today:

- `cortex init`
- `cortex store`
- `cortex search`
- `cortex recall`
- `cortex verify`
- `cortex trust-ledger verify --full`
- `cortex export`
- `cortex status`

These commands are the shortest path to product value: store a fact, retrieve it, verify integrity, detect tampering, and export evidence.

## Public Python Surface

The public Python import contract is aligned with the distribution name:

```python
from cortex_persist import AsyncCortexClient, CortexClient, CortexEngine
```

Use this import path for examples, SDK docs, and public integration guides.

## REST API Contract

The REST API is available today in self-hosted beta mode from a cloned repository checkout:

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install -e ".[api]"
uvicorn cortex.api:app --port 8000
```

Supported core endpoints:

| Method | Path | Contract |
| :--- | :--- | :--- |
| `GET` | `/v1/status` | Engine health and status |
| `POST` | `/v1/facts` | Store a fact |
| `POST` | `/v1/search` | Semantic search |
| `GET` | `/v1/projects/{project}/facts` | Recall facts for a project |
| `DELETE` | `/v1/facts/{fact_id}` | Deprecate a fact |

Operator-only endpoints in the same beta API mode:

| Method | Path | Contract |
| :--- | :--- | :--- |
| `POST` | `/v1/admin/keys` | Create an API key |
| `GET` | `/v1/admin/keys` | List API keys |

## Explicitly Outside The Supported Core

The following surfaces should not be advertised as generally available today:

- Public PyPI installation such as `pip install cortex-persist`
- Public npm installation such as `npm install @cortex-persist/sdk`
- Worker-stack and Aether-facing commands as part of the main public CLI promise
- Managed cloud distribution
- Repo-internal orchestration, swarm, and sovereign command families that exist in-tree but do not belong to the current public contract
- Extended API and SDK surfaces that are present in code but not yet part of the supported-core guarantee

## How To Read The Rest Of The Repo

- [System Map](system-map.md) explains the repository taxonomy.
- [CORTEX Native Technologies](cortex-native-technologies.md) explains the trust capabilities behind the product.
- [Architecture](architecture.md) explains how the surfaces fit together.

Those pages describe the broader codebase. This page defines the support boundary.

## Related References

- [Canonical Demo](canonical-demo.md)
- [API Reference](api.md)
- [Operations](OPERATIONS.md)
- [Architecture](architecture.md)
