# Repository Map — Ownership Contract

This document defines the boundary contract between Cortex-Persist (trust layer) and all satellite surfaces.
Any directory not listed under **In Repo** belongs outside this repository by design.

## Cortex-Persist = Trust Layer

**What lives here:**
- `cortex/` — core engine, persistence, verification, coordination, runtime
- `cortex-sdk/` — typed Python client SDK
- `cortex-hypervisor/` — scheduling and daemon coordination
- `tests/` — automated test suite
- `docs/` — architecture, security, axioms, contributing, operations
- `scripts/` — repo tooling (boundary guard, inventory, CI helpers)
- `api/` — FastAPI routes and OpenAPI surface
- `compliance-check/` — EU AI Act compliance tooling
- `benchmarks/` — performance validation
- `config/` — runtime configuration
- `examples/` — minimal usage examples

**What does NOT live here:**

| Satellite | Category | Correct Home |
|-----------|----------|--------------|
| `cortexpersist-landing` | Marketing site | `cortex-marketing` repo |
| `cortexpersist-com` | Web org site | `cortex-web` repo |
| `cortexpersist-org` | Web org site | `cortex-web` repo |
| `cortexpersist-dev` | Dev portal | `cortex-docs-site` repo |
| `cortexpersist-docs` | Docs site | `cortex-docs-site` repo |
| `cortexpersist-api` | API gateway/proxy | `cortex-gateway` repo |
| `CortexDash.app` | macOS app shell | `cortex-dashboard` repo |
| `dashboard` | Web dashboard | `cortex-dashboard` repo |
| `experimental_ui` | UI experiments | `cortex-labs` repo |
| `awwwards-engine` | Design system | `cortex-labs` repo |
| `aether_drop` | Agent demo | `cortex-labs` repo |
| `auramem` | Memory UX app | `cortex-labs` repo |
| `sovereign-agency` | Agency surface | separate repo |
| `airdrops` | Distribution | separate repo |
| `Rework_POC_Generations` | Audio/media | personal repo |
| `White_Pony_Master` | Audio/media | personal repo |
| `White_Pony_Stems` | Audio/media | personal repo |
| `Sources` | Media assets | personal repo |
| `ShadowStudio` | Studio surface | personal repo |
| `cortex_eguzkia/` | MOSKV-universe expansion | `cortex-labs` repo |
| `cortex_iturria/` | MOSKV-universe expansion | `cortex-labs` repo |
| `cortex-hypervisor/` | Scheduling daemon — dedup with `cortex/daemon` | Merge into `cortex/` or `cortex-labs` |
| `cortex-sdk/` | Client SDK — dedup with `cortex/` public surface | Merge into `sdk/python/` or standalone repo |

## Enforcement

The boundary is enforced programmatically:
- `scripts/check_core_boundary.py` — local and CI gate
- `.github/workflows/core-boundary.yml` — blocks any PR/push that reintroduces forbidden dirs

## Non-Goals

Cortex-Persist is **not**:
- A monorepo for all CORTEX-adjacent surfaces
- A showcase demo repository
- A personal project dumping ground
- A distribution mechanism for media or marketing assets

If it cannot be tested by `pytest tests/` and does not contribute to trust-layer guarantees,
it does not belong here.
