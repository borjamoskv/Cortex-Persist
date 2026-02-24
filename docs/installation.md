# Installation

## Requirements

- **Python 3.10** or later
- **macOS**, **Linux**, or **Windows**
- SQLite 3.42+ (included with Python 3.11+; for 3.10, `pysqlite3` is auto-loaded if available)

---

## Install from PyPI

```bash
pip install cortex-memory
```

### Optional Extras

=== "API Server"
    ```bash
    pip install cortex-memory[api]
    ```
    Includes FastAPI, Uvicorn, and HTTPX for the REST API, dashboard, and MCP server.

=== "Development"
    ```bash
    pip install cortex-memory[dev]
    ```
    Includes pytest, pytest-cov, pytest-asyncio, and HTTPX for testing.

=== "Google ADK"
    ```bash
    pip install cortex-memory[adk]
    ```
    Adds Google Agent Developer Kit integration.

=== "Billing"
    ```bash
    pip install cortex-memory[billing]
    ```
    Stripe integration for SaaS subscription management.

=== "Everything"
    ```bash
    pip install cortex-memory[all]
    ```
    Installs all optional dependencies.

---

## Install from Source

```bash
git clone https://github.com/borjamoskv/cortex.git
cd cortex
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
```

---

## Verify Installation

```bash
cortex --version
# cortex-memory, version 8.0.0a1
```

---

## First Steps

```bash
# Initialize the database
cortex init

# Check system health
cortex status

# Store your first fact
cortex store my-project "Redis uses skip lists for sorted sets" --tags "redis,data-structures"
```

This creates the database at `~/.cortex/cortex.db` with the full schema (facts, transactions, embeddings, consensus, and more).

---

## Platform-Specific Notes

### macOS

- Notifications use `osascript` (Notification Center)
- Daemon installs as a `launchd` agent (`~/Library/LaunchAgents/`)
- Native Keychain integration via `pyobjc`

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
- **[CLI Reference](cli.md)** — All 38 commands
- **[Architecture](architecture.md)** — How it works under the hood
