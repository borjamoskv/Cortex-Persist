# Developer Guide

> Everything you need to contribute to CORTEX.

---

## Project Structure

```
cortex/
├── cortex/                     # Main Python package
│   ├── engine/                # Core engine (CortexEngine, mixins, ledger)
│   ├── api/                   # FastAPI application setup
│   ├── routes/                # REST API route handlers (20 modules)
│   ├── auth/                  # Authentication & RBAC
│   ├── embeddings/            # Local (ONNX) & API embedding providers
│   ├── consensus/             # Multi-agent WBFT consensus + reputation
│   ├── facts/                 # Fact lifecycle management
│   ├── graph/                 # Knowledge graph (SQLite + Neo4j backends)
│   ├── search/                # Advanced semantic search
│   ├── memory/                # Memory management layer
│   ├── compaction/            # Auto-compaction strategies
│   ├── compliance/            # EU AI Act compliance reports
│   ├── audit/                 # Audit trail generation
│   ├── crypto/                # AES-256-GCM vault
│   ├── daemon/                # Self-healing watchdog (13 monitors)
│   ├── notifications/         # Telegram + OS notification bus
│   ├── sync/                  # JSON ↔ DB bidirectional sync
│   ├── timing/                # Developer time tracking
│   ├── telemetry/             # OpenTelemetry-compatible tracing
│   ├── mcp/                   # Model Context Protocol server
│   ├── cli/                   # 38 CLI commands (Click)
│   ├── migrations/            # Versioned schema migrations
│   ├── gate/                  # Rate limiting & validation
│   ├── storage/               # SQLite + Turso backends
│   ├── thinking/              # Thought Orchestra, semantic router
│   ├── episodic/              # Session snapshots
│   ├── llm/                   # Multi-provider LLM support
│   ├── types/                 # Type definitions
│   ├── utils/                 # Shared utilities
│   └── config.py              # Centralized configuration
├── tests/                      # 1,162+ test functions
├── docs/                       # Documentation (mkdocs-material)
├── examples/                   # Quickstart examples
├── sdks/                       # Python & JavaScript SDKs
├── scripts/                    # Build & maintenance scripts
├── infra/                      # Infrastructure configs
├── benchmarks/                 # Performance benchmarks
└── notebooks/                  # Jupyter notebooks
```

---

## Setup

```bash
# Clone and install
git clone https://github.com/borjamoskv/cortex.git
cd cortex
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"

# Initialize database
cortex init

# Run tests
make test
```

---

## Engine Architecture

CORTEX has **two engine implementations**:

### 1. `CortexEngine` (Composite Orchestrator)

Located in `cortex/engine/__init__.py`. The main entry point used by both CLI and API:

- Composes `FactManager`, `EmbeddingManager`, and `ConsensusManager`
- Provides both sync and async methods via `SyncCompatMixin`
- Manages database connections and ledger
- Delegates CRUD to mixins: `StoreMixin`, `QueryMixin`, `ConsensusMixin`

```python
from cortex.engine import CortexEngine

engine = CortexEngine(db_path="my.db", auto_embed=True)
engine.init_db_sync()

# Store
fact_id = engine.store_sync("project-x", "Python is great", fact_type="knowledge")

# Search
results = engine.search_sync("programming languages")
```

### 2. `AsyncCortexEngine` (API Engine)

Located in `cortex/engine_async.py`. Used by FastAPI routes for maximum concurrency:

- Takes a `CortexConnectionPool` for connection management
- All methods are `async`
- Handles transaction logging and hash chain maintenance

```python
pool = await CortexConnectionPool.create(db_path, pool_size=5)
engine = AsyncCortexEngine(pool, db_path)

fact_id = await engine.store(project="x", content="Hello", fact_type="knowledge")
```

---

## Adding a New Route

1. **Create the route file** `cortex/routes/my_feature.py`:

```python
from fastapi import APIRouter, Depends
from cortex.auth import AuthResult, require_permission
from cortex.api_deps import get_async_engine

router = APIRouter(tags=["my-feature"])

@router.get("/v1/my-feature")
async def my_endpoint(
    auth: AuthResult = Depends(require_permission("read")),
    engine = Depends(get_async_engine),
):
    # All queries automatically scoped to auth.tenant_id
    return {"status": "ok"}
```

2. **Register in** `cortex/api.py`:

```python
from cortex.routes.my_feature import router as my_feature_router
app.include_router(my_feature_router)
```

---

## Adding a New CLI Command

1. **Create the command file** `cortex/cli/my_cmds.py`:

```python
import click
from cortex.engine import CortexEngine

@click.command("my-command")
@click.argument("project")
@click.option("--db", default=None)
def my_command(project: str, db: str | None):
    """Description of what this command does."""
    engine = CortexEngine(db_path=db)
    engine.init_db_sync()
    # ... your logic
    click.echo("Done!")
```

2. **Register in** `cortex/cli/__init__.py`:

```python
from cortex.cli.my_cmds import my_command
cli.add_command(my_command)
```

---

## Adding a New MCP Tool

1. **Add the tool** in `cortex/mcp/server.py`:

```python
@server.tool()
async def cortex_my_tool(param: str) -> str:
    """Description for the AI agent."""
    engine = get_engine()
    # ... your logic
    return result
```

2. **Add guard rules** in `cortex/mcp/guard.py` if needed.

---

## Configuration System

All config lives in `cortex/config.py`. Variables are loaded from environment at import time:

```python
from cortex import config

# Read value
print(config.DB_PATH)

# Refresh after env changes
config.reload()
```

!!! warning "Test Isolation"
    Always call `config.reload()` after patching environment variables. The global `conftest.py` does this automatically.

---

## Writing Tests

### Test Isolation

Tests use temporary databases and `config.reload()` for isolation:

```python
import pytest
from cortex.engine import CortexEngine

@pytest.fixture
def engine(tmp_path):
    db = tmp_path / "test.db"
    eng = CortexEngine(db_path=db, auto_embed=False)
    eng.init_db_sync()
    return eng

def test_store(engine):
    fid = engine.store_sync("test", "Hello world", fact_type="knowledge")
    assert fid > 0
```

### API Tests

```python
from fastapi.testclient import TestClient
import cortex.api as api_mod

def test_health(tmp_path):
    os.environ["CORTEX_DB"] = str(tmp_path / "test.db")
    from cortex import config
    config.reload()

    with TestClient(api_mod.app) as c:
        resp = c.get("/health")
        assert resp.status_code == 200
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_store(pool, engine):
    fact_id = await engine.store(project="test", content="async fact")
    assert fact_id > 0
```

### Running Tests

```bash
make test          # All tests (60s timeout)
make test-fast     # Exclude slow tests
make test-slow     # Only slow tests (graph, embeddings)
make lint          # Ruff linter
make format        # Auto-format
```

---

## i18n System

All user-facing error messages go through `cortex/i18n.py`:

```python
from cortex.i18n import get_trans

msg = get_trans("error_not_found", lang="es")
# → "Recurso no encontrado"
```

Supported languages: `en`, `es`, `eu` (Basque).

To add a new translation:
1. Add entry to `TRANSLATIONS` dict in `i18n.py`
2. Provide `en`, `es`, and `eu` translations
3. Use `get_trans("your_key", lang)` in route handlers

---

## Schema Migrations

When adding a new table:

1. Add `CREATE TABLE` to `cortex/schema.py`
2. Add it to the `ALL_SCHEMA` list
3. Create a migration file in `cortex/migrations/` for existing databases
4. Test with `cortex init` on a fresh DB and `cortex migrate` on existing

---

## Coding Conventions

| Convention | Rule |
|:---|:---|
| **Sync methods** | Suffix with `_sync` (e.g., `store_sync()`) |
| **Async methods** | No suffix (e.g., `store()`) |
| **SQL** | Always parameterized (`?` placeholders, never f-strings) |
| **Secrets** | Environment variables only, never hardcoded |
| **Logging** | `logging.getLogger("cortex.module_name")` |
| **Dates** | ISO 8601 via `cortex.temporal.now_iso()` |
| **Hashing** | `cortex.canonical.canonical_json()` for deterministic serialization |
| **Error handling** | Specific exceptions (`sqlite3.Error`, `ValueError`), never bare `except` |
| **Types** | Full type hints, `py.typed` marker included |
| **Formatting** | Ruff (line length 100, target Python 3.10) |

---

## Continuous Documentation

CORTEX uses `mkdocstrings` for auto-generating API documentation from source code. When you add new methods, update docstrings, or modify classes, the changes will reflect without manual Markdown edits.

### Local Live Reload

Run the local development server with hot-reloading:

```bash
make docs-serve
```

Any changes to `.md` files in `docs/` OR changes to Python docstrings in `cortex/` will trigger an instant rebuild and reload the browser automatically.

### Documenting Python Code

Use Google-style docstrings with type hints for optimal mkdocstrings parsing:

```python
def my_function(param: int) -> str:
    """Description of the function.

    Args:
        param (int): The parameter descriptor.

    Returns:
        str: Description of the return value.
    """
    return str(param)
```

---

## Pull Request Checklist

- [ ] Tests pass (`make test`)
- [ ] Lint passes (`make lint`)
- [ ] New features have tests
- [ ] New endpoints have Pydantic models
- [ ] New CLI commands have `--help` text
- [ ] New tables added to `schema.py` + `ALL_SCHEMA`
- [ ] Secrets use environment variables
- [ ] SQL uses parameterized queries
- [ ] `config.reload()` used in new test fixtures
