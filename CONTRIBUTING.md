# Contributing to CORTEX

Thank you for your interest in contributing to CORTEX! 🧠

## How to Contribute

### Reporting Bugs

1. Open an [issue](../../issues) with the title `[BUG] short description`.
2. Include: Python version, CORTEX version, OS.
3. Steps to reproduce the bug.
4. Expected output vs actual output.

### Proposing Features

1. Open an [issue](../../issues) with the title `[FEATURE] short description`.
2. Explain the use case.
3. If possible, include an example of the desired API.

### Pull Requests

1. Fork the repo.
2. Create a branch: `git checkout -b feature/my-feature`.
3. Make your changes.
4. Run tests: `pytest tests/ -v`.
5. Commit with a descriptive message.
6. Push and open a PR.

### Code Style

- Python 3.10+
- Formatter: [Ruff](https://docs.astral.sh/ruff/)
- Line length: 100
- Type hints ensuring compatibility
- Docstrings for public functions

### Development Setup

```bash
# Clone
git clone https://github.com/borjamoskv/cortex.git
cd cortex

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[all]"

# Run tests
pytest tests/ -v

# Run benchmark
python scripts/benchmark.py --iterations 10
```

## Code of Conduct

Be respectful. Period. We do not tolerate any form of harassment or discrimination.

## License

By contributing, you accept that your code will be distributed under the [BSL 1.1](LICENSE).
