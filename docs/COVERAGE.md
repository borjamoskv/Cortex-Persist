# Code Coverage Guide

This document describes the code coverage configuration and targets for the Cortex-Persist project.

## Coverage Architecture

The project uses **component-based coverage tracking** to measure test coverage across different Python packages separately, allowing for module-by-module coverage improvement.

### Measured Packages

| Package | Path | Coverage Target | Flag |
|---------|------|----------------|------|
| **Core** | `cortex/` | 80% | `core` |
| **SDK** | `cortex-sdk/cortex_persist/` | 75% | `sdk` |
| **SDKs** | `sdks/` | 70% | `sdks` |
| **API** | `api/` | 70% | `api` |

## Configuration Files

### .codecov.yml

The main Codecov configuration file defines:

- **Flags**: Separate tracking for each package component
- **Component Management**: Per-module coverage targets
- **Ignore Patterns**: Excludes tests, docs, examples, experimental code
- **Coverage Status**: Project-wide target of 80%, patch target of 85%

### CI Workflow (.github/workflows/ci.yml)

The CI pipeline runs pytest with coverage measurement across all packages:

```bash
pytest tests/ \
  --cov=cortex \
  --cov=cortex-sdk/cortex_persist \
  --cov=sdks \
  --cov=api \
  --cov-report=xml \
  --cov-report=term-missing
```

## Excluded Paths

The following paths are excluded from coverage measurement:

- `tests/**` - Test files themselves
- `scripts/**` - Utility scripts
- `docs/**` - Documentation
- `benchmarks/**` - Performance benchmarks
- `examples/**` - Example code
- `experimental/**` - Experimental/prototype code
- `cortex-core/**` - Standalone scripts (not a package)
- `**/__pycache__/**` - Python cache files
- `**/conftest.py` - Pytest configuration
- `**/.scratch/**` - Temporary/scratch files
- `bounty/**`, `bounty_hunt/**` - Bounty-related code
- `skills/compiled_skills/**` - Generated skill code

## Coverage Targets Strategy

### Current Targets (Phase 1)

- **Core (cortex/)**: 80% - The main package, highest priority
- **SDK (cortex-sdk/)**: 75% - Client SDK for external use
- **SDKs (sdks/)**: 70% - Additional platform-specific SDKs
- **API (api/)**: 70% - API endpoints

### Path to 100% (Incremental Approach)

As suggested in the original requirements, achieving 100% coverage should be done **module by module**:

1. **Phase 1** (Current): Establish baseline coverage for all packages
2. **Phase 2**: Improve Core package to 90%+
3. **Phase 3**: Improve SDK package to 85%+
4. **Phase 4**: Improve remaining packages incrementally

This approach ensures:
- ✅ No mixing of SDK coverage with core coverage
- ✅ Clear visibility into which modules need attention
- ✅ Gradual, sustainable improvement
- ✅ No "noise" from untestable generated code

## Viewing Coverage Reports

### Local Development

Run tests with coverage locally:

```bash
# Install dependencies
pip install -e ".[dev,api]"

# Run tests with coverage for all packages
pytest tests/ \
  --cov=cortex \
  --cov=cortex-sdk/cortex_persist \
  --cov=sdks \
  --cov=api \
  --cov-report=html \
  --cov-report=term-missing

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### CI/CD

Coverage reports are automatically:
1. Generated during CI test runs (Python 3.13 only)
2. Uploaded to [Codecov](https://codecov.io)
3. Posted as comments on pull requests
4. Tracked over time with historical graphs

## Component Flags

Codecov flags allow viewing coverage per component:

- **`core`**: View coverage for the main `cortex/` package
- **`sdk`**: View coverage for the Python SDK
- **`sdks`**: View coverage for platform SDKs
- **`api`**: View coverage for API endpoints

Each flag can be viewed independently on the Codecov dashboard.

## Best Practices

1. **Write tests for new code**: All new features should include tests
2. **Maintain existing coverage**: Don't decrease coverage on modified files
3. **Focus on critical paths first**: Prioritize high-risk code for coverage
4. **Use coverage to find bugs**: Uncovered code often reveals edge cases
5. **Don't game the metrics**: Coverage is a tool, not a goal

## Troubleshooting

### Coverage not showing for my package

Ensure the package is:
1. Listed in `--cov=<package>` in CI workflow
2. Defined as a flag in `.codecov.yml`
3. Not in the ignore list

### Coverage dropping unexpectedly

Check:
1. Whether new code was added without tests
2. If tests are being skipped in CI
3. Codecov dashboard for detailed file-by-file breakdown

## References

- [Codecov Documentation](https://docs.codecov.com/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
