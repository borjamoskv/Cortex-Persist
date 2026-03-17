# Cortex-Persist

**A trust layer for stateful agent systems: persistent memory, auditable trace, guarded execution, and concurrency-safe coordination primitives for regulated and high-integrity environments.**

🌐 **English** | [Español](README.es.md) | [中文](README.zh.md)

`cortex-persist v0.3.0b2` · Engine `v8` · Python `3.10+`

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-cortexpersist.dev-brightgreen)](https://cortexpersist.dev)

---

## 1. What is it

Cortex-Persist is a **local-first cryptographic trust substrate** for autonomous AI systems. It transforms stochastic generative output into a deterministic, auditable ledger — persisting every decision, enforcing validation boundaries, and maintaining cryptographic chain-of-custody from inference to storage.

It does not replace memory backends (Mem0, Zep, custom stores). It **certifies** them.

## 2. What problem it solves

| Problem | Consequence |
|---------|-------------|
| Agents hallucinate their own history | Entropy compounds silently — past decisions are invented, not retrieved |
| No causal opacity audit trail | Impossible to answer "why did the agent reach that conclusion?" |
| EU AI Act Article 12 requirements | Regulated deployments need immutable operational logs and crypto-verifiable traces |
| Multi-agent consensus gaps | Swarms lack standardized coordination, breaking global state across async tasks |

## 3. Quickstart

```bash
pip install cortex-persist
```

```bash
# Store a decision fact
cortex store --type decision --project fin-agent "Approved credit #4292 (Score: 88)"

# Verify cryptographic integrity
cortex verify "8f4a2b9e"
# → [✔] VERIFIED: Hash chain intact. Merkle root sealed.

# Generate compliance report
cortex compliance-report
```

```python
from cortex.engine import CortexEngine

engine = CortexEngine()
await engine.store(
    type="decision",
    project="fin-agent",
    content="Approved credit #4292",
    confidence="C4"
)
report = await engine.verify_ledger()
```

## 4. Core architecture

```text
cortex/
├── engine/       # Core CRUD, causal graph orchestration, mixin composition
├── memory/       # Vector store integration (sqlite-vec) and local persistence
├── guards/       # Admission, contradiction, dependency, injection-detection
├── verification/ # Cryptographic integrity, Merkle sealing
├── consensus/    # Byzantine multi-agent arbitration (WBFT)
├── trace/        # Causal DAGs, lineage, taint propagation (Ω₁₃)
├── compliance/   # EU AI Act Article 12 audit surface
├── runtime/      # Event hooks, lifecycle abstractions
├── api/          # FastAPI REST interface (optional: [api])
├── cli/          # Click + Rich CLI
└── mcp/          # Model Context Protocol adapter
```

Full repository topology and decision rationale: [docs/architecture/repo-map.md](docs/architecture/repo-map.md).

## 5. Use cases

- **Regulated AI systems** — Fintech, GovTech, HealthTech pipelines requiring cryptographically auditable AI decision logs (EU AI Act Article 12 compliance surface)
- **Agent swarms** — Shared knowledge synchronization via `cortex.consensus` + `SovereignLock` for high-contention async coordination
- **Autonomous agents** — Long-term semantic memory with `sqlite-vec` vector indexing natively integrated with causal lineage

## 6. Project status

| Dimension | Status |
|-----------|--------|
| Version | `v0.3.0b2` |
| Core engine stability | Beta — cryptographic chain validated under crash scenarios |
| Public API surface | Converging toward `v1.0.0` |
| Concurrency testing | File-backed, `:memory:`, shared-cache, lock contention, cancellation |
| Compliance surface | EU AI Act Article 12 primitives operational |

## 7. Repository Evidence

Generated automatically on every push to `main` via CI.

- Inventory: [`artifacts/inventory.md`](artifacts/inventory.md)
- File tree snapshot: [`artifacts/tree.txt`](artifacts/tree.txt)
- Repository stats: [`artifacts/stats.json`](artifacts/stats.json)

This repository intentionally contains only the trust-layer surface.
Satellite surfaces (apps, dashboards, marketing, experiments) live outside by design:

| Boundary | In Repo | Out of Repo |
|----------|---------|-------------|
| Runtime / Persistence / Verification | ✅ | |
| Coordination / Consensus / Trace | ✅ | |
| Dashboards / Apps / Marketing / Experiments | | ✅ |

Boundary contract: [`docs/architecture/repo-map.md`](docs/architecture/repo-map.md)
CI enforcement: [`.github/workflows/core-boundary.yml`](.github/workflows/core-boundary.yml)

## 8. Docs, API, security

| Resource | Link |
|----------|------|
| Architecture | [docs/architecture/repo-map.md](docs/architecture/repo-map.md) |
| Compliance | [docs/compliance/](docs/compliance/) |
| Security policy | [SECURITY.md](SECURITY.md) |
| Contributor contract | [CONTRIBUTING.md](CONTRIBUTING.md) + [AGENTS.md](AGENTS.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| Full docs site | [cortexpersist.dev](https://cortexpersist.dev) |

## 9. Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) before opening an issue or PR.

The core rejects any PR that:
- Bifurcates `ledger.py` integrity without test coverage
- Bypasses guards on memory write paths
- Introduces blocking calls (`time.sleep`) in async contexts
- Injects third-party dependencies without an asymptotic performance justification
