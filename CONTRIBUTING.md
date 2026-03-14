# Contributing to CORTEX

Thank you for your interest in CORTEX. We welcome contributions of all kinds.

Before making changes, read [AGENTS.md](./AGENTS.md) — the operational contract for contributors and coding agents working inside this repository.

## Contribution Guide

This file covers local setup, quality checks, and the basic pull request flow.

Before touching critical trust surfaces, also read:

- [AGENTS.md](./AGENTS.md) — operational contract and invariants
- [docs/CONTRIBUTING.md](./docs/CONTRIBUTING.md) — deep change protocols
- [docs/SECURITY_TRUST_MODEL.md](./docs/SECURITY_TRUST_MODEL.md) — trust boundaries and verification model

## Development Setup

```bash
# Clone the repo
git clone https://github.com/borjamoskv/cortex.git
cd cortex

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install with all optional deps
pip install -e ".[all]"

# Verify setup
pytest tests/ -v --tb=short -x
```

## Running the Test Suite

```bash
# Full suite (1,000+ tests)
pytest tests/ -v --tb=short

# Single file
pytest tests/test_engine.py -v

# With coverage
pytest tests/ --cov=cortex --cov-report=term-missing

# Fast smoke test
pytest tests/ -x --timeout=30
```

## Code Quality

We use **Ruff** for linting and formatting:

```bash
# Check
ruff check cortex/ tests/
ruff format --check cortex/ tests/

# Auto-fix
ruff check --fix cortex/ tests/
ruff format cortex/ tests/

# Type check
pyright cortex/
```

## Making Changes

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/my-change`
3. **Make your changes** — keep commits focused and atomic
4. **Add tests** for new functionality
5. **Run the full test suite** to confirm nothing is broken
6. **Submit a Pull Request** against `master`

### Commit Message Convention

```text
<type>: <short description>

Types: feat, fix, docs, test, refactor, ci, chore
```

Examples:

- `feat: add graph-based memory traversal`
- `fix: correct Merkle checkpoint hash calculation`
- `docs: expand privacy shield documentation`

## Pull Requests

Keep pull requests small, test-backed, and scoped to one change surface when possible.

Before opening a PR:

- run tests
- run Ruff
- run Pyright
- confirm CI passes
- update docs if public behavior changed

For schema, ledger, async, API, or trust-surface changes, follow the deep protocols in
[`docs/CONTRIBUTING.md`](./docs/CONTRIBUTING.md).

## Creating a Plugin

Use the scaffold generator:

```bash
python scripts/create_plugin.py my-plugin --description "Does something cool"
```

This generates a complete working plugin with manifest, API spec, Dockerfile, tests, and docs.

## Questions?

- Open a [GitHub Discussion](https://github.com/borjamoskv/cortex/discussions)
- Email: [borja@moskv.com](mailto:borja@moskv.com)

## License

By contributing, you agree that your contributions will be licensed under Apache License 2.0.
