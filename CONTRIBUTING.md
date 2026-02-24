# Contributing to CORTEX

Thank you for your interest in contributing to CORTEX! 🚀

## Quick Start

```bash
git clone https://github.com/borjamoskv/cortex.git
cd cortex
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Development Rules

1. **All facts are hash-chained.** Never bypass the ledger.
2. **Tests are mandatory.** No PR merges without passing CI.
3. **Privacy Shield is sacred.** Never weaken secret detection patterns.
4. **Local-first always.** Every feature must work with SQLite alone.

## Pull Request Process

1. Fork the repo and create your branch from `main`
2. Add tests for any new functionality
3. Ensure `pytest` passes with no failures
4. Update documentation if needed
5. Submit PR using the template

## Code Style

- **Formatter**: Ruff (`ruff format`)
- **Linter**: Ruff (`ruff check`)
- **Line length**: 100 characters
- **Type hints**: Required for all public APIs

## Architecture

See the [README](README.md) for the architecture diagram. Key principle:

> Every layer trusts nothing. Verify everything.

## License

By contributing, you agree that your contributions will be licensed under the BSL-1.1 license.
