<p align="center">
  <img src="assets/marketing/social-preview.png" alt="CORTEX Persist — tamper-evident memory for AI agents" width="720">
</p>

<h1 align="center">CORTEX Persist</h1>

<p align="center">
  <strong>Verifiable memory and decision lineage for high-stakes AI workflows.</strong>
</p>

<p align="center">
  Local-first. SHA-256 hash-chained. Merkle-sealed. Audit-ready.
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/Cortex-Persist/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/Cortex-Persist?style=social" alt="GitHub Stars"></a>&nbsp;&nbsp;
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"></a>&nbsp;
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>&nbsp;
  <a href="https://github.com/borjamoskv/Cortex-Persist/actions"><img src="https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg" alt="CI"></a>&nbsp;
  <a href="https://codecov.io/gh/borjamoskv/Cortex-Persist"><img src="https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg" alt="Codecov"></a>&nbsp;
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg" alt="PyPI"></a>
</p>

<p align="center">
  <a href="docs/product-surface.md">Public Product Surface</a> ·
  <a href="docs/quickstart.md">Quickstart</a> ·
  <a href="docs/course/README.md">Course Suite</a> ·
  <a href="docs/api.md">API</a> ·
  <a href="docs/mcp.md">MCP</a> ·
  <a href="docs/SECURITY_TRUST_MODEL.md">Security Model</a> ·
  <a href="ROADMAP.md">Roadmap</a>
</p>

---

CORTEX Persist gives teams shipping AI into high-stakes workflows verifiable memory,
tamper-evident decision lineage, and exportable evidence. It adds hash-chained records and
verification commands so teams can inspect what happened instead of reconstructing it later.

## What It Is

CORTEX Persist is designed for workflows where a plain log is not enough.

- Store structured facts and decisions.
- Hash-chain every write into a tamper-evident ledger.
- Search and recall persisted knowledge.
- Verify the ledger when you need evidence, not guesses.
- Export artifacts for reviews, audits, and incident response.

It sits alongside your existing stack. Use it with your current database, observability tools,
and vector search where that makes sense.

## Best Fit

- High-stakes AI workflows that can take irreversible actions.
- Support, approval, pricing, finance, and compliance flows.
- Long-running systems that need traceable state transitions.
- Teams that need a defensible record after the fact.

## Not A Replacement For

- Observability platforms such as Datadog or ELK.
- Dedicated vector databases for broad ephemeral retrieval.
- Human review, legal review, or compliance judgment.

## Install

### From PyPI

```bash
pip install cortex-persist
```

Add extras only when you need them:

```bash
pip install "cortex-persist[api]"   # REST API
pip install "cortex-persist[mcp]"   # MCP server
```

### From Source

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Quickstart

```bash
# Initialize the local ledger
cortex init

# Store a fact
cortex store my-project "Redis uses skip lists for sorted sets" --tags "redis,data-structures"

# Store a decision
cortex store my-project "We chose FastAPI over Flask for async support" --type decision

# Search and recall
cortex search "async web framework" --project my-project
cortex recall my-project

# Verify integrity
cortex verify 1
cortex trust-ledger verify

# Generate a compliance snapshot
cortex compliance-report
```

If you want a guided path, see [docs/quickstart.md](docs/quickstart.md).

## Python Integration

```python
import asyncio
from cortex import CortexEngine


async def main() -> None:
    engine = CortexEngine()
    try:
        fact_id = await engine.store(
            project="demo-agent",
            content="User approved transaction $5,000",
            fact_type="decision",
        )

        results = await engine.search("transaction approval", top_k=3, project="demo-agent")
        ledger = await engine.verify_ledger()

        assert fact_id
        assert results
        assert ledger.get("valid") is True
    finally:
        await engine.close()


asyncio.run(main())
```

## Advanced In-Repo Surfaces

The repository also contains broader operator surfaces: swarm orchestration, additional CLI groups,
advanced HTTP routes, dashboards, and script catalogs. Those pieces are available in-repo, but
they are not the recommended first integration target.

The default FastAPI app and MCP server stay on the narrower product surface first. Broader HTTP
routes and MCP tool families are opt-in via flags such as `CORTEX_ENABLE_EXPERIMENTAL_API=1` and
`CORTEX_ENABLE_EXPERIMENTAL_MCP=1`.

Use [docs/product-surface.md](docs/product-surface.md) as the canonical boundary between the
verifiable-memory product surface and the broader repository tooling.

## Documentation

- [Public Product Surface](docs/product-surface.md)
- [Course Suite (EN/ES/ZH)](docs/course/README.md)
- [Quickstart](docs/quickstart.md)
- [Installation](docs/installation.md)
- [CLI Reference](docs/cli.md)
- [REST API Reference](docs/api.md)
- [MCP Server](docs/mcp.md)
- [Security & Trust Model](docs/SECURITY_TRUST_MODEL.md)
- [Architecture](docs/architecture.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).

*Built by [borjamoskv.com](https://borjamoskv.com) and [cortexpersist.com](https://cortexpersist.com)*
