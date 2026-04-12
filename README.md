<p align="center">
  <img src="assets/marketing/social-preview.png" alt="CORTEX Persist — Tamper-evident memory for AI agents" width="720">
</p>

> Verifiable memory and decision records for AI agents.

**Track what an agent saw, decided, and changed - with tamper-evident history.**

Local-first. SHA-256 hash-chained. Merkle checkpoints. Audit-ready.

[![GitHub Stars](https://img.shields.io/github/stars/borjamoskv/Cortex-Persist?label=GitHub%20Stars)](https://github.com/borjamoskv/Cortex-Persist/stargazers)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml?query=branch%3Amain)
[Quickstart](#quickstart) · [Canonical Demo](docs/canonical-demo.md) · [Supported Core](docs/supported-core.md) · [System Map](docs/system-map.md) · [Native Technologies](docs/cortex-native-technologies.md) · [Enterprise Readiness](ENTERPRISE_READINESS.md) · [Diligence Checklist](DUE_DILIGENCE_CHECKLIST.md) · [Deployment Hardening](DEPLOYMENT_HARDENING.md) · [API](docs/api.md) · [Security Model](docs/SECURITY_TRUST_MODEL.md) · [Support](SUPPORT.md) · [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md)

CORTEX Persist adds a verification layer around agent memory and decision state. It sits between your runtime and your storage so facts, decisions, and derived state become reviewable, tamper-evident records instead of mutable application state. If stored context changes after the fact, verification fails.

## Why CORTEX

| Feature | Logs & Observability | CORTEX Persist (Verification Layer) |
| :--- | :--- | :--- |
| **Trust Model** | "Trust the process" | **"Verify the record"** |
| **Tamper Detection** | Weak (DB mutation is silent) | **Cryptographic** (SHA-256 + Merkle) |
| **Compliance Proof** | Requires manual reconstruction | **Portable JSON Audit Packs** |
| **Decision Review** | Ambiguous context reconstruction | **Verifiable decision history** |

> Logs tell you what happened. CORTEX helps you verify what context an agent used, what it decided, and whether that record has changed since. [**Review a real verification proof.**](examples/audit_proof_artifact.json)

## Supported Core Today

This repository contains much more code than the product surface that is safe to promise today. The supported core is the minimum public contract that currently works as a product.
If you are evaluating CORTEX for the first time, start with the [Canonical Demo](docs/canonical-demo.md) and then use [Supported Core](docs/supported-core.md) as the contract boundary.

| Surface | Current Status |
| :--- | :--- |
| Install path | Source install from this repository: `git clone ... && pip install .` |
| Public Python import | `cortex_persist` |
| Supported CLI flow | `init`, `store`, `search`, `recall`, `verify`, `trust-ledger verify --full`, `export`, `status` |
| API mode | Available from source with `pip install -e ".[api]"`, currently beta as a self-hosted surface |
| Not part of supported core | Public PyPI release, public npm release, worker stacks, managed cloud, and broad repo-internal orchestration surfaces |

The subsystem taxonomy below describes the whole repository. It does not redefine the supported product boundary. The canonical support contract lives in [Supported Core](docs/supported-core.md).
If you are evaluating rather than implementing, skip straight to [Canonical Demo](docs/canonical-demo.md), [Supported Core](docs/supported-core.md), and [Enterprise Readiness](ENTERPRISE_READINESS.md).

## System Map

CORTEX now exposes a stable subsystem taxonomy for navigating the codebase and architecture without forcing an immediate package rename:

| Subsystem | Role | Existing Package Surfaces |
| :--- | :--- | :--- |
| **CORTEX Hypercore** | Trust kernel, guards, ledger, and persistence boundary | `engine/`, `ledger/`, `guards/`, `verification/`, `crypto/`, `database/`, `storage/`, `security/`, `auth/` |
| **CORTEX Overmind** | Orchestration, swarm control, coordination, and agent runtime | `agents/`, `consensus/`, `gateway/`, `mcp/`, `worker/`, `extensions/swarm/`, `extensions/sovereign/`, `extensions/federation/`, `extensions/hypervisor/`, `extensions/manifold/` |
| **CORTEX Deepforge** | Synthesis, reasoning, perception, and code-generation surfaces | `composer/`, `mcts/`, `shannon/`, `extensions/llm/`, `extensions/thinking/`, `extensions/evolution/`, `extensions/training/`, `extensions/skills/`, `extensions/perception/` |
| **CORTEX Primeflow** | Execution runtime, APIs, services, event delivery, and operational flows | `api/`, `routes/`, `services/`, `events/`, `http/`, `cli/`, `telemetry/`, `extensions/automation/`, `extensions/daemon/`, `extensions/sync/`, `extensions/notifications/`, `extensions/timing/` |
| **CORTEX Coreshift** | Memory evolution, indexing, migration, audit, and state transitions | `memory/`, `facts/`, `search/`, `embeddings/`, `graph/`, `compaction/`, `enrichment/`, `migrations/`, `audit/`, `compliance/`, `forensics/` |
| **CORTEX Ouroboros** | Economic extraction, market intelligence, MEV, and dark forest forensics | `ouroboros-sniper/`, `extensions/economy/`, `extensions/trading/`, `extensions/market/` |

These names are architectural groupings over the current repository, not replacement Python package names. The canonical mapping lives in [System Map](docs/system-map.md).

## Core Trust Capabilities

CORTEX groups five core capabilities that show up across the repository. The names below map to the canonical architecture, but the practical value is straightforward:

1. **Deterministic admission checks**: generated claims are validated before they become durable state.
2. **Hash continuity and checkpoint verification**: ledger entries can be checked across events, batches, and rollback boundaries.
3. **Explicit handling of uncertain or tainted memory**: uncertain, stale, or contradictory state stays visible instead of being silently blended in.
4. **Rollback-aware write flows**: non-trivial mutations follow compensating steps instead of leaving partial state behind.
5. **Isolated self-modification paths**: runtime code generation can be contained, tested, and validated before it affects persistent state.

The canonical definition and module mapping live in [CORTEX Native Technologies](docs/cortex-native-technologies.md).

## Use Cases

1. **Autonomous Agents:** Record what context was present when an agent made a critical decision (for example, executing a trade or sending a legal email).
2. **Multi-Agent Systems:** Trace state propagation across agents and workflows.
3. **Compliance-Heavy Environments:** Produce audit trails for finance, security, and regulated operations.
4. **Post-incident forensics:** detect silent mutation, tampering, or replayed state.
5. **Trust-sensitive AI products:** ship verifiable memory and decisions instead of relying on mutable logs.

## Why not just logs or a vector DB?

Traditional logging and standard vector stores help you observe systems. They do not give you a verifiable record of memory and decisions. CORTEX adds that layer without forcing you to replace your stack.

| Feature                    | Standard Logs (Datadog/ELK) | Standard Vector DB (Pinecone/Qdrant) | **CORTEX Persist**                        |
|:---------------------------|:----------------------------|:-------------------------------------|:------------------------------------------|
| **Primary Goal**           | Observability & Debugging   | Semantic Search & RAG                | **Verifiable memory and decision records** |
| **Write Integrity**        | Overwritable / Editable     | Silent CRUD operations               | **Append-Only + Cryptographic Hash**      |
| **Fact Mutability**        | Easy (API/Admin access)     | Easy (API/Admin access)              | **Tamper-evident, append-oriented records** |
| **Evidence Export**        | Text dumps                  | JSON extracts                        | **Portable audit packs**                  |

> **See a real artifact**: [View exported audit pack](examples/audit_proof_artifact.json)

### What CORTEX does NOT replace (Non-Goals)

- **CORTEX is not a Semantic Search primary DB:** Continue using Qdrant, Pinecone, or Milvus for purely ephemeral RAG chunks. CORTEX stores the *decisions* and core *facts*.
- **CORTEX is not an Observability Platform:** Continue using Datadog or ELK for server metrics, APM, and basic string logs. 
- **CORTEX does not stop hallucinations:** A verifiable record can still contain a wrong model conclusion. CORTEX makes that state auditable; it does not make it true.

## Deployment Matrix

- **Tamper-evident memory:** append-only ledger for facts, decisions, and state transitions.
- **Hash-linked records:** SHA-256 chaining across stored entries.
- **Batch integrity proofs:** Merkle checkpoints for efficient verification at scale.
- **Deterministic audit exports:** reproducible evidence for internal review and regulated workflows.
- **Drop-in positioning:** works on top of existing memory stores instead of replacing your stack.

| Environment | Status | Storage / Scaling |
| :--- | :--- | :--- |
| **Local-Only** | ✅ **Most Mature** | SQLite + WAL + built-in Vector Search. Best fit today for single-node, operator-managed deployments. |
| **Self-Hosted** | 🟡 **Beta** | Multi-tenant. API-driven. Redis cache. Pluggable to your infra. |
| **Cloud-Ready** | ⏳ **Roadmap** | AlloyDB/PostgreSQL + Qdrant. For distributed massive swarms. |

## Experimental Surfaces

The repository also contains worker, swarm, and orchestration modules beyond the supported core. Treat those areas as beta, experimental, or internal until they are documented as part of the public support boundary. The public README should not be read as a promise that every repo-internal command or deployment file is production-supported today.

## Enterprise Readiness

CORTEX is still on a beta product line, but the repository now exposes the basic due-diligence surfaces a serious buyer or platform team expects:

- **Stable governance surface:** [Support](SUPPORT.md), [Security Policy](SECURITY.md), [Contributing](CONTRIBUTING.md), and [Code of Conduct](CODE_OF_CONDUCT.md)
- **Stable technical entrypoints:** [Architecture](docs/architecture.md), [Security Model](docs/SECURITY_TRUST_MODEL.md), [API](docs/api.md), and [Operations](docs/OPERATIONS.md)
- **Release and supply-chain controls:** release workflow, signing path, CI, CodeQL, SBOM generation, dependency audit, and container scanning
- **Deployment and buyer validation guides:** [DEPLOYMENT_HARDENING.md](DEPLOYMENT_HARDENING.md) and [DUE_DILIGENCE_CHECKLIST.md](DUE_DILIGENCE_CHECKLIST.md)
- **Candid diligence summary:** strengths, current limits, and evaluation checklist in [ENTERPRISE_READINESS.md](ENTERPRISE_READINESS.md)

If you are evaluating CORTEX for acquisition, procurement, or internal platform adoption, start with [ENTERPRISE_READINESS.md](ENTERPRISE_READINESS.md) and [DUE_DILIGENCE_CHECKLIST.md](DUE_DILIGENCE_CHECKLIST.md).

## Canonical Demo

This assumes the CLI is already installed. On a clean machine, start with the quickstart just below.
The fully reproducible version, including a tamper drill, lives in [Canonical Demo](docs/canonical-demo.md).

```bash
# 1. Start the ledger
$ cortex init

# 2. Store a memory
$ cortex store risk-bot "Transaction flagged: IP mismatch" --type decision --source agent:risk-bot
[✓] Stored fact #<FACT_ID> in risk-bot

# 3. Verify integrity
$ cortex verify <FACT_ID>
[✔] VERIFIED: Hash chain intact.

# 4. Verify the ledger and fact set
$ cortex trust-ledger verify --full
[✔] Ledger is VALID

# 5. Export portable evidence
$ cortex export --project risk-bot --format json --out ./risk-bot-audit.json
```

## Quickstart

Start logging tamper-evident memories locally in under a minute.
The supported install path today is source installation from this repository while public package publication is being finalized.
The distribution keeps `cortex` as the operational module path for CLI and API entrypoints, while the public Python import surface is `cortex_persist`.

```bash
# 1. Clone, install from source, and initialize
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install .
cortex init

# 2. Store a memory (SHA-256 hashed and chained to prior facts)
cortex store risk-bot "Transaction flagged: IP mismatch" --type decision --source agent:risk-bot

# 3. Verify the trust ledger
cortex trust-ledger verify --full
```

## Integration

CORTEX wraps your existing state management. It does not replace your embeddings or vector search.

```python
import asyncio
from cortex_persist import CortexEngine

async def main() -> None:
    engine = CortexEngine()

    receipt = await engine.store_fact(
        content="User approved transaction $5,000",
        fact_type="decision",
        project="fin-fraud-bot",
        tenant_id="customer-123",
    )

    assert await engine.verify(receipt.hash) is True

asyncio.run(main())
```

## Performance

*Typical execution on a standard cloud instance (4 vCPU, 16 GB RAM).*

| Operation | Median | P95 | Notes |
| :--- | :--- | :--- | :--- |
| **Memory Write** | ~18 ms | ~35 ms | Local SQLite + SHA-256 |
| **Verify Record** | ~5 ms | ~12 ms | Single block validation |
| **Merkle Checkpoint** | ~85 ms | ~140 ms | Aggregating 10k records |
| **Report Export** | ~400 ms | ~800 ms | Lineage traversal |

---

## Threat Model Summary (Trust Boundaries)

CORTEX treats generative AI output as untrusted input until it passes deterministic checks.
- **Generated output is validated before persistence:** model output only becomes durable memory after guards, schema checks, and write-path validation.
- **Mutation paths are constrained:** agents cannot write arbitrary state outside the validated mutation flow.
- **Tamper evidence complements access control:** if someone edits stored records after the fact, the hash chain no longer verifies.

> Read the cryptographic guarantees in the [Security Model](docs/SECURITY_TRUST_MODEL.md).

---

## Documentation

Repo-versioned documentation lives in [`docs/`](docs/documentation-boundary.md) and is the source of truth for the published docs surface. The website may mirror these pages, but GitHub readers should not have to leave the repository to validate the core product surface.

- [**Quickstart**](#quickstart) — Install, store, verify.
- [**Canonical Demo**](docs/canonical-demo.md) — Reproducible proof of store → verify → tamper detection → export.
- [**Supported Core**](docs/supported-core.md) — Exact public contract that is safe to promise today.
- [**Enterprise Readiness**](ENTERPRISE_READINESS.md) — Buyer-facing maturity, risk, and diligence summary.
- [**Due Diligence Checklist**](DUE_DILIGENCE_CHECKLIST.md) — Reproducible technical and security evaluation steps.
- [**Deployment Hardening**](DEPLOYMENT_HARDENING.md) — Production-oriented guardrails for self-hosted deployments.
- [**Support Policy**](SUPPORT.md) — Support channels, response targets, and release support window.
- [**Repository Governance**](REPO_GOVERNANCE.md) — Ownership, review expectations, and change safety rules.
- [**Maintainers**](MAINTAINERS.md) — Current maintainer model and stewardship boundaries.
- [**Version Support**](VERSION_SUPPORT.md) — Supported release line expectations.
- [**Release Process**](RELEASE_PROCESS.md) — Tagged Python release workflow, provenance, and artifact signing.
- [**System Map**](docs/system-map.md) — Canonical subsystem taxonomy for Hypercore, Overmind, Deepforge, Primeflow, Coreshift, and Ouroboros.
- [**CORTEX Native Technologies**](docs/cortex-native-technologies.md) — Canonical definition of the platform's five core trust capabilities.
- [**API Reference**](docs/api.md) — SDK primitives, REST startup, and core endpoints.
- [**Security Model**](docs/SECURITY_TRUST_MODEL.md) — Cryptographic invariants, trust boundaries, and verification guarantees.
- [**Architecture**](docs/architecture.md) — System topology, deployment modes, and critical trust surfaces.
- [**Operations**](docs/OPERATIONS.md) — Runbooks, deployment posture, and operational checks.
- [**Roadmap**](ROADMAP.md) — Deployment phases and scaling logic.
- [**Contributing**](CONTRIBUTING.md) — Development workflow and contribution rules.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).

*Built by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
