# Contributing to CORTEX

Thank you for your interest in CORTEX! We welcome contributions of all kinds.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/borjamoskv/cortex.git
cd cortex

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install with dev dependencies
pip install -e ".[all]"

# Verify setup
pytest tests/ -v --tb=short -x
```

## Running the Test Suite

```bash
# Full suite (1,276+ tests)
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
```

## Making Changes

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/my-change`
3. **Make your changes** — keep commits focused and atomic
4. **Add tests** for new functionality
5. **Run the full test suite** to confirm nothing is broken
6. **Submit a Pull Request** against `master`

### Commit Message Convention

```
<type>: <short description>

Types: feat, fix, docs, test, refactor, ci, chore
```

Examples:
- `feat: add graph-based memory traversal`
- `fix: correct Merkle checkpoint hash calculation`
- `docs: expand privacy shield documentation`

## Pull Request Guidelines

- PRs should target `master`
- Ensure CI passes (lint + tests + security audit)
- Include a description of **what** changed and **why**
- Link related issues with `Closes #123`

## Architecture Overview

```
cortex/
├── api.py              # FastAPI REST endpoints
├── cli/                # Click-based CLI (38 commands)
├── engine.py           # Core CortexEngine
├── audit/              # Immutable ledger & Merkle trees
├── consensus/          # WBFT multi-agent consensus
├── gate/               # Trust Gateway (RBAC, Privacy Shield)
├── search/             # Vector + semantic search
├── sovereign/          # Self-healing daemon & observability
├── storage/            # SQLite, AlloyDB, Turso backends
└── mcp/                # Model Context Protocol server
```

For detailed architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Creating a Plugin

Use the scaffold generator:

```bash
python scripts/create_plugin.py my-plugin --description "Does something cool"
```

This generates a complete working plugin with manifest, API spec, Dockerfile, tests, and docs.

## Questions?

- Open a [GitHub Discussion](https://github.com/borjamoskv/cortex/discussions)
- Email: borja@moskv.com

## License

By contributing, you agree that your contributions will be licensed under BSL-1.1.
