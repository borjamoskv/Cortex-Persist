<!-- [C5-REAL] Exergy-Maximized -->
# CONTRIBUTING.md — BABYLON-60 Persist v8.0

Package: babylon60 v1.0.0
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

## Commit Message Standard

All commits **must** follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

### Allowed types

`feat` · `fix` · `chore` · `refactor` · `docs` · `test` · `ci` · `build` · `perf` · `style` · `revert` · `release`

### Rules

| Rule | Constraint |
|---|---|
| Header max length | 100 chars |
| Subject max length | 72 chars |
| Subject case | lower-case or sentence-case |
| Emoji in subject | **forbidden** |
| Codenames in subject | **forbidden** (e.g. `VOID-MAX`, `Operation X`) |

### Examples

```bash
# ✅ Good
feat(pipeline): implement E2E orchestration layer
fix(ci): make Trivy scan non-blocking
refactor(search): modularize into vector, hybrid, text packages
docs: add CODE_OF_CONDUCT.md

# ❌ Bad — will be rejected by commitlint
🚀 CORTEX Singularity Foundational Push
Operation VOID-MAX — Silicon-Native SIMD
Add GitHub Actions workflow for publishing to PyPI
[WIP] Fix product foundation naming
MEJORAlo v9.1 checkpoint: Inicio
```

### Enforcement

Commit messages are validated by `commitlint` via `pre-commit` (commit-msg stage). Install hooks:

```bash
pre-commit install --hook-type commit-msg
pre-commit install
```

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
- [`docs/architecture.md`](./docs/architecture.md)
- [`SECURITY.md`](./SECURITY.md)
