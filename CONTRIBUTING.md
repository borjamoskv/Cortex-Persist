# CONTRIBUTING.md — CORTEX Persist

Package: cortex-persist v0.3.0b1
Engine: v8
License: Apache-2.0
Python: >=3.10

## Purpose

This file covers local setup, quality checks, and the basic pull request flow.

Before touching critical trust surfaces, also read:

- [AGENTS.md](./AGENTS.md) — operational contract and invariants
- [docs/CONTRIBUTING.md](./docs/CONTRIBUTING.md) — deep change protocols
- [docs/SECURITY_TRUST_MODEL.md](./docs/SECURITY_TRUST_MODEL.md) — trust boundaries and verification model

## Development Setup

Clone the repository and install in editable mode with development dependencies:

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install -e ".[dev]"
```

If you are working on API, cloud, ADK, or full-surface integration paths, install the relevant extras:

```bash
pip install -e ".[api]"
pip install -e ".[cloud]"
pip install -e ".[adk]"
pip install -e ".[all]"
```

## Quality Checks

Run the required checks before opening a pull request:

```bash
pytest tests/ -v --cov=cortex
ruff check cortex/
pyright cortex/
```

If your change touches API surfaces, also run the relevant API tests.
If your change touches CLI behavior, test the CLI path explicitly.

## Pull Requests

Keep pull requests small, test-backed, and scoped to one change surface when possible.

Before opening a PR:

- run tests
- run Ruff
- run Pyright
- confirm CI passes
- update docs if public behavior changed

For schema, ledger, async, API, or trust-surface changes, follow the deep protocols in [`docs/CONTRIBUTING.md`](./docs/CONTRIBUTING.md).

## Basic Contribution Rules

- Preserve tenant-aware behavior in public data paths.
- Keep CLI modules thin; do not move business logic into command wrappers.
- Prefer explicit failure over permissive fallback behavior.
- Add or update tests for every behavior change.
- Use type hints on public functions.
- Catch specific exceptions rather than broad ones.
- Keep dependency additions justified and reflected in project metadata.

## Documentation Expectations

Update documentation when you change:

- public APIs
- CLI behavior
- trust boundaries
- validation behavior
- storage or migration semantics
- operational procedures

## Related Documents

- [`AGENTS.md`](./AGENTS.md)
- [`docs/CONTRIBUTING.md`](./docs/CONTRIBUTING.md)
- [`docs/SECURITY_TRUST_MODEL.md`](./docs/SECURITY_TRUST_MODEL.md)
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- [`SECURITY.md`](./SECURITY.md)
