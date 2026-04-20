<p align="center">
  <img src="assets/marketing/social-preview.png" alt="CORTEX Persist — Tamper-evident memory for AI agents" width="720">
</p>

<h1 align="center">CORTEX Persist</h1>

<p align="center">
  <strong>Cryptographic memory integrity for AI agents</strong>
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
  <a href="#quickstart">Quickstart</a> · <a href="#documentation">Docs</a> · <a href="docs/SECURITY_TRUST_MODEL.md">Security Model</a> · <a href="ROADMAP.md">Roadmap</a> · <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

## What is CORTEX Persist?

CORTEX Persist is a **local-first trust layer** for AI agents. It makes agent memory tamper-evident through cryptographic hash chains, giving you verifiable audit trails instead of anecdotes.

**In short:** Store facts. Verify integrity. Generate compliance reports. All local. All auditable.

### What it does

- **Tamper-evident storage**: Facts are SHA-256 hash-chained. Any mutation after the fact breaks verification.
- **Cryptographic audit trails**: Every write creates immutable ledger entries. Verification is O(1).
- **Local-first**: SQLite + built-in vector search. No external dependencies required for core functionality.
- **Compliance-ready**: EU AI Act Article 12 audit pack generation built-in.

### What it is NOT

- **Not a vector database**: Use Qdrant/Pinecone for ephemeral RAG. CORTEX stores *decisions* and *facts*.
- **Not an observability platform**: Use Datadog/ELK for server metrics and APM.
- **Not a hallucination preventer**: A cryptographically logged lie is still a lie — it's just an *auditable* lie.

## Use Cases

- **Autonomous agents**: Prove what context an agent had when making irreversible decisions
- **Multi-agent systems**: Trace state propagation across agents and workflows
- **Compliance environments**: Generate audit trails for finance, security, and regulated operations
- **Post-incident forensics**: Detect silent mutations, tampering, or replayed state
- **Trust-sensitive AI products**: Ship memory with evidence, not vibes

## The Supported Path Today

CORTEX Persist is built on a **local-first SQLite core** with cryptographic hash-chaining and built-in vector search. This is the stable, production-ready path.

**What's stable:**
- Core trust layer: `init` → `store` → `verify` → `export`
- Local SQLite + WAL mode + optional vector search
- SHA-256 hash-chained ledger with Merkle checkpoints
- Cryptographic audit pack generation
- CLI and Python SDK

**What's beta:**
- REST API server (`cortex-persist[api]`)
- MCP (Model Context Protocol) integration (`cortex-persist[mcp]`)
- Multi-tenant mode with RBAC

**What's experimental** (not supported for production):
- Cloud backends (Postgres/AlloyDB, Qdrant Cloud, Redis)
- Distributed consensus and federation
- Swarm coordination and agent handoff surfaces

See [docs/PRODUCT-CORE.md](docs/PRODUCT-CORE.md) for complete stability tier definitions.

## Quickstart

Get started in under 5 minutes with the stable local-first core.

### Install

```bash
pip install cortex-persist
```

This installs the core trust layer with deterministic fallback embeddings — enough for the supported `init → store → verify` flow.

**Optional: Add semantic search**

```bash
pip install "cortex-persist[embeddings]"
```

For local ONNX-based embeddings instead of deterministic fallback vectors.

**Full installation options:** See [docs/installation.md](docs/installation.md)

### Initialize

```bash
cortex init
```

Creates `~/.cortex/cortex.db` with the ledger and fact schema.

### Store Facts

```bash
# Store a decision
cortex memory store my-project "Approved loan application #443" --type decision

# Store knowledge
cortex memory store my-project "Redis uses skip lists for sorted sets" --tags "redis,data-structures"

# Store with explicit source
cortex memory store my-project "Rate limit: 100 req/min" --source "agent:claude"
```

Every fact is automatically hash-chained into an immutable ledger.

### Verify Integrity

```bash
# Verify the entire ledger
cortex ledger verify

# Generate a compliance report
cortex compliance-report
```

### Search (Optional)

If you installed `[embeddings]`, you can run semantic search:

```bash
cortex search "how are sorted sets implemented?"
```

### Python SDK

```python
import asyncio
from cortex import CortexEngine

async def main():
    engine = CortexEngine()

    # Store a fact
    fact_id = await engine.store(
        project="my-agent",
        content="Approved loan application #443",
        fact_type="decision",
        tenant_id="customer-123",
    )

    # Verify ledger integrity
    result = await engine.verify_ledger()
    assert result.get("valid") is True

asyncio.run(main())
```

**Full example:** See [`examples/demo_canonical.py`](examples/demo_canonical.py) for a complete walkthrough.

---

## Extended Surfaces (Beta / Experimental)

Beyond the core trust layer, CORTEX includes optional server and orchestration surfaces. These require additional installation and are in beta or experimental status.

### REST API Server (Beta)

```bash
pip install "cortex-persist[api]"
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Interactive docs: `http://localhost:8484/docs`

See [docs/api.md](docs/api.md) for the full API reference.

### Model Context Protocol (Beta)

CORTEX speaks MCP, making it a plug-in for AI IDEs like Claude Code, Cursor, and Windsurf.

```bash
pip install "cortex-persist[mcp]"
python -m cortex.mcp
```

See [docs/quickstart.md#mcp-server](docs/quickstart.md#run-as-mcp-server) for MCP integration details.

### Daemon & Background Services (Experimental)

```bash
pip install "cortex-persist[daemon]"
cortex daemon start
```

Runs specialized monitors for health, security, and memory compaction. See [docs/cli.md](docs/cli.md) for full command reference.

---

## Non-Goals

**What CORTEX Persist is explicitly NOT designed for:**

- **Not a primary semantic search database**: Use Qdrant, Pinecone, or Weaviate for large-scale ephemeral RAG workloads.
- **Not application observability**: Use Datadog, New Relic, or ELK for server metrics, traces, and APM.
- **Not a graph database**: Use Neo4j or Memgraph if your primary need is complex relationship querying.
- **Not a real-time event bus**: Use Kafka, RabbitMQ, or NATS for high-throughput message streaming.
- **Not a source-of-truth prevention tool**: A cryptographically logged lie is still a lie — CORTEX makes it *auditable*, not *impossible*.

CORTEX is a trust layer that sits *alongside* your existing stack, not a replacement for specialized infrastructure.

---

## Security & Trust Model

CORTEX treats all generative output as conjecture until it passes deterministic validation boundaries.

**Trust boundaries:**
- **Write path**: Proposals → Guards → Schema validation → Encryption → Ledger → Persistence
- **Hash continuity**: SHA-256 chaining with Merkle checkpoints
- **Tenant isolation**: Multi-tenant data separation enforced at all memory layers
- **Encrypted at rest**: Sensitive fact content and metadata are encrypted before storage

**What CORTEX guarantees:**
- Cryptographic traceability of persisted facts
- Tamper-evident audit trails
- Deterministic rejection of structurally invalid inputs
- Tenant-aware data isolation

**What CORTEX does NOT guarantee:**
- Semantic truth of stored content
- Correctness of upstream models or tools
- Safety if guards or verification surfaces are bypassed

Read the full threat model and cryptographic guarantees in [docs/SECURITY_TRUST_MODEL.md](docs/SECURITY_TRUST_MODEL.md).

---

## Documentation

| Document | Description |
| :--- | :--- |
| [**Quickstart Guide**](docs/quickstart.md) | Extended CLI walkthrough and usage examples |
| [**Installation**](docs/installation.md) | Platform-specific notes and optional extras |
| [**CLI Reference**](docs/cli.md) | Complete command reference (90+ commands) |
| [**API Reference**](docs/api.md) | REST API endpoints and SDK usage |
| [**Security & Trust Model**](docs/SECURITY_TRUST_MODEL.md) | Cryptographic guarantees and threat model |
| [**Product Core**](docs/PRODUCT-CORE.md) | Stability tiers (Stable/Beta/Experimental) |
| [**Architecture**](docs/architecture.md) | System design and module topology |
| [**Roadmap**](ROADMAP.md) | Upcoming features and capability bands |
| [**Contributing**](CONTRIBUTING.md) | How to contribute to CORTEX Persist |

---

## Performance

Local SQLite performance on typical hardware (4 vCPU, 16 GB RAM):

| Operation | Median | P95 |
| :--- | :--- | :--- |
| Memory Write | ~18 ms | ~35 ms |
| Verify Record | ~5 ms | ~12 ms |
| Merkle Checkpoint | ~85 ms | ~140 ms |
| Audit Export | ~400 ms | ~800 ms |

---

## License

Apache License 2.0. See [LICENSE](LICENSE).

---

*Built by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
