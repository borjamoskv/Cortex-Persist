# MCP Toolbox for Databases — CORTEX Integration

Exposes `cortex.db` as read-only MCP tools for any MCP-compatible client.

## Architecture

```
Agent → MCP Protocol → Toolbox (port 5000) → cortex.db (reads)
Agent → MCP Protocol → CORTEX MCP Server   → cortex.db (writes)
```

## Prerequisites

```bash
# Install the Toolbox binary (Go required)
go install github.com/googleapis/genai-toolbox@latest
```

## Quick Start

```bash
# Default: reads from ~/.cortex/cortex.db
bash cortex/mcp/toolbox/run_toolbox.sh

# Custom DB path
CORTEX_DB=/path/to/cortex.db bash cortex/mcp/toolbox/run_toolbox.sh

# Custom port
TOOLBOX_PORT=8080 bash cortex/mcp/toolbox/run_toolbox.sh
```

## Available Tools

| Tool | Description | Parameters |
|:-----|:-----------|:-----------|
| `query-facts` | Search facts by project, type, confidence | `project`, `fact_type`, `min_confidence`, `limit` |
| `query-ghosts` | List knowledge gaps by status | `status`, `project`, `limit` |
| `query-decisions` | Retrieve architectural decisions | `project`, `limit` |
| `query-signals` | Read signal bus events | `event_type`, `project`, `limit` |
| `cortex-stats` | Aggregate knowledge base stats | *(none)* |

## Toolsets

- **`cortex-readonly`** — All 5 tools (trusted agents)
- **`cortex-summary`** — Stats only (untrusted/external consumers)

## Connecting from IDE

### Gemini CLI

```bash
gemini --tool "http://localhost:5000"
```

### VS Code (via MCP extension)

Add to `.vscode/settings.json`:

```json
{
  "mcp.servers": {
    "cortex-toolbox": {
      "url": "http://localhost:5000"
    }
  }
}
```

## Security Model

- **Read-only by design** — no INSERT/UPDATE/DELETE statements
- **Parameterized queries** — prevents SQL injection
- **Toolset access control** — limit which tools agents can access
- **Writes route through CORTEX MCP server** — preserves ledger integrity and SQLite write-lock safety
