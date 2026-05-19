---
description: Build and run CORTEX-Persist project
---

# 🔨 Build CORTEX-Persist

## Prerequisites

```bash
# Required environment
python --version  # >= 3.10
pip install -e ".[dev]"
```

## Quick Build (Dev)

// turbo
1. Install and verify:
```bash
pip install -e ".[dev]" --quiet && python -c "import cortex; print(f'cortex {cortex.__version__}')"
```

## Test Suite

// turbo
2. Run tests:
```bash
pytest tests/ -v --tb=short -q 2>&1 | tail -30
```

## Lint & Type Check

// turbo
3. Quality checks:
```bash
ruff check cortex/ --fix && ruff format cortex/ --check
```

## Clean Build

// turbo
4. Clean and rebuild from scratch:
```bash
pip install -e ".[dev]" --force-reinstall --quiet && pytest tests/ -v --tb=short -q 2>&1 | tail -30
```

## CI

Quality gates run automatically on PR to `main`. See `.github/workflows/quality_gates.yml`.
