<!-- [C5-REAL] Exergy-Maximized -->
# Installation

## Requirements

- **Python 3.10** or later
- **macOS**, **Linux**, or **Windows**
- SQLite 3.42+ (included with Python 3.11+; for 3.10, `pysqlite3` is auto-loaded if available)

---

## Install from PyPI *(preferred)*

The quickest way to get started:

```bash
pip install babylon60
```

This installs the supported core flow with deterministic fallback embeddings, which is enough for:
- `cortex --version`
- `cortex init`
- `store -> verify -> export`

After installing, verify it works:

```bash
cortex --version
cortex init
```

If you run in a headless environment without OS Keychain support, set `CORTEX_MASTER_KEY` or `CORTEX_VAULT_KEY` explicitly before the first write.

On macOS, enable native keychain support with:

```bash
pip install "babylon60[platform]"
```

### Optional Extras

=== "Local Embeddings"
    ```bash
    pip install "babylon60[embeddings]"
    ```
    Adds `sentence-transformers` and `onnxruntime` for local semantic embeddings and reranking instead of deterministic fallback vectors.

=== "Acceleration"
    ```bash
    pip install "babylon60[acceleration]"
    ```
    Adds `numba` for optional JIT acceleration in specialized DSP and swarm modules.

=== "API Server"
    ```bash
    pip install babylon60[api]
    ```
    Includes FastAPI, Uvicorn, HTTPX, and email validation for the REST API and dashboard.

=== "MCP Server"
    ```bash
    pip install babylon60[mcp]
    ```
    Adds FastMCP runtime dependencies, HTML extraction helpers, and filesystem watchers for MCP and resilient gateway flows.

=== "Daemon / Sidecars"
    ```bash
    pip install babylon60[daemon]
    ```
    Adds `aiofiles`, `aiohttp`, `arq`, and `watchdog` for daemon, SSE, relay, and background queue surfaces.

=== "Platform Bindings"
    ```bash
    pip install babylon60[platform]
    ```
    Adds `pyobjc` bindings required by macOS keychain integration.

=== "Authoring / YAML"
    ```bash
    pip install babylon60[authoring]
    ```
    Adds `PyYAML` for agent configs, genesis specs, and other YAML-driven authoring surfaces.

=== "Development"
    ```bash
    pip install babylon60[dev]
    ```
    Includes pytest, pytest-cov, pytest-asyncio, and HTTPX for testing.

=== "Google ADK"
    ```bash
    pip install babylon60[adk]
    ```
    Adds Google Agent Developer Kit integration.

=== "Billing"
    ```bash
    pip install babylon60[billing]
    ```
    Stripe integration for SaaS subscription management.

=== "Everything"
    ```bash
    pip install babylon60[all]
    ```
    Installs all optional dependencies.

---

## Install from Source *(development / contributing)*

Use this path when you want to contribute to BABYLON-60 or run the latest unreleased code:

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Add extras on top only if you need those surfaces during development, for example `pip install -e ".[api,mcp,daemon,authoring,embeddings,dev]"`.

---

## Verify Installation

```bash
cortex --version
# cortex, version 0.3.0b7
```

---

## First Steps

```bash
# Initialize the database
cortex init

# Check system health
cortex status

# Store your first fact
cortex memory store my-project "Redis uses skip lists for sorted sets" --tags "redis,data-structures"
```

This creates the database at `~/.cortex/cortex.db` with the base ledger/fact schema plus optional vector and extended tables when the runtime supports them.

---

## Platform-Specific Notes

### macOS

- Notifications use `osascript` (Notification Center)
- Daemon installs as a `launchd` agent (`~/Library/LaunchAgents/`)
- Native Keychain integration via `pyobjc` (install `babylon60[platform]` if needed)

### Linux

- Notifications use `notify-send` (libnotify)
- Daemon installs as a `systemd` user service (`~/.config/systemd/user/`)
- No root/sudo required

### Windows

- Notifications use PowerShell Toast
- Daemon installs as a Task Scheduler job (triggered at logon)
- Compatible with WSL2 for development

See [Cross-Platform Guide](cross_platform_guide.md) for full architecture details.

---

## Next Steps

- **[Quickstart](quickstart.md)** — Store, search, verify in 5 minutes
- **[CLI Reference](cli.md)** — Core commands documented
- **[Architecture](architecture.md)** — How it works under the hood
