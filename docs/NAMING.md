# CORTEX Persist — Canonical Naming Reference

This document is the authoritative source of truth for all public-facing names across the CORTEX Persist project.

---

## Canonical Names

| Surface | Name | Notes |
|:---|:---|:---|
| **PyPI package** | `cortex-persist` | `pip install cortex-persist` |
| **Python import** | `cortex` | `from cortex import CortexEngine` |
| **CLI entry point** | `cortex` | `cortex init`, `cortex store`, `cortex verify FACT_ID`, `cortex ledger verify` |
| **Cloud SDK import** | `cortex_persist` | From `cortex-sdk/` — thin HTTP wrapper for the hosted API |
| **JS/TS SDK** | `@cortex-persist/sdk` | Not yet published on npm — roadmap item |

---

## Rationale

### PyPI Package: `cortex-persist`

The root `pyproject.toml` defines the canonical PyPI distribution name as `cortex-persist`. This is the authoritative package. The `cortex-sdk/` and `sdks/python/` directories are **separate, experimental thin-client SDKs** for the hosted cloud API — they are not the same package and are not yet published.

### Python Import: `cortex`

The Python source tree lives under the `cortex/` directory at the root of the repository. When users install `pip install cortex-persist`, they import from `cortex`:

```python
from cortex import CortexEngine
```

This is the **local-first engine** — no cloud dependency, no API key required.

### CLI: `cortex`

The CLI entry point is `cortex`, defined in `[project.scripts]` in `pyproject.toml`. All CLI examples should use `cortex` as the command prefix.

```bash
cortex init
cortex store my-agent "Important fact" --type decision
cortex verify 1
cortex ledger verify
```

### Cloud SDK: `cortex_persist` (from `cortex-sdk/`)

The `cortex-sdk/` directory contains a **thin HTTP wrapper SDK** for the hosted CORTEX Persist cloud API. This SDK uses the Python import `cortex_persist` and is a **different package** from the local engine.

> ⚠️ **Not yet published.** The cloud SDK (`cortex-sdk/`) is not yet deployed to PyPI or production. Do not use `from cortex_persist import CortexMemory` in examples unless you are explicitly documenting the cloud SDK.

### JS/TS SDK: `@cortex-persist/sdk`

The JavaScript/TypeScript SDK lives in `sdks/js/` and will eventually be published as `@cortex-persist/sdk` on npm.

> ⏳ **Roadmap.** Not yet published. `npm install @cortex-persist/sdk` returns 404 until the first npm release.

---

## Anti-Patterns to Avoid

| ❌ Wrong | ✅ Correct | Why |
|:---|:---|:---|
| `from cortex_persist import CortexMemory` (in core docs) | `from cortex import CortexEngine` | Cloud SDK, not local engine |
| `pip install cortex_persist` | `pip install cortex-persist` | Underscore is wrong |
| `npm install @cortex-persist/sdk` (without caveat) | Add "⏳ Coming Soon" note | Not yet on npm |
| Referring to the package as "Cortex Persist SDK" | "CORTEX Persist" | Canonical product name |

---

## Related Files

- `pyproject.toml` — Authoritative package metadata
- `cortex-sdk/README.md` — Cloud SDK documentation
- `sdks/js/README.md` — JS/TS SDK documentation
- `docs/sdks.md` — Full SDK comparison
