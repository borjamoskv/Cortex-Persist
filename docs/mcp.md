# MCP Server

CORTEX implements the **Model Context Protocol (MCP)** — an open standard for connecting AI agents to tools and data sources. This makes CORTEX a plug-in for any MCP-compatible AI IDE.

---

## Compatible IDEs

| IDE | Status |
|:---|:---|
| **Claude Code** (Anthropic) | ✅ Native |
| **Cursor** | ✅ Native |
| **OpenClaw** | ✅ Native |
| **Windsurf** | ✅ Native |
| **Antigravity** | ✅ Native |

---

## Start the MCP Server

```bash
python -m cortex.mcp
```

Or explicitly:

```bash
python -m cortex.mcp.server
```

The server starts a stdio-based MCP transport, which is the standard for IDE integrations.

---

## Configuration

### Claude Code (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.mcp"],
      "env": {
        "CORTEX_DB": "~/.cortex/cortex.db"
      }
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.mcp"]
    }
  }
}
```

### Antigravity (VS Code settings)

```json
{
  "mcp": {
    "servers": {
      "cortex": {
        "command": "python",
        "args": ["-m", "cortex.mcp"]
      }
    }
  }
}
```

---

## Available Tools

### Core Memory Tools

| Tool | Description |
|:---|:---|
| `cortex_store` | Store a fact with automatic hash chaining and embedding |
| `cortex_search` | Hybrid semantic search across all facts |
| `cortex_status` | System health, statistics, and database info |

### Trust & Compliance Tools

| Tool | Description |
|:---|:---|
| `cortex_ledger_verify` | Full ledger integrity check — walks the entire hash chain |
| `cortex_verify_fact` | Cryptographic verification certificate for a single fact |
| `cortex_audit_trail` | Generate a timestamped, hash-verified audit log |
| `cortex_compliance_report` | EU AI Act Article 12 compliance snapshot with score |
| `cortex_decision_lineage` | Trace how an agent arrived at any conclusion |

---

## Tool Details

### `cortex_store`

**Parameters:**

| Param | Type | Required | Description |
|:---|:---|:---:|:---|
| `project` | string | ✅ | Project namespace |
| `content` | string | ✅ | Fact content |
| `fact_type` | string | — | `knowledge`, `decision`, `error`, `ghost`, `config`, `bridge` |
| `tags` | string | — | Comma-separated tags |
| `source` | string | — | Source identifier (auto-detected if omitted) |

**Example:**

```
Store this decision in CORTEX: "We chose PostgreSQL over MySQL for JSON support"
→ cortex_store(project="my-api", content="We chose PostgreSQL...", fact_type="decision")
```

### `cortex_search`

**Parameters:**

| Param | Type | Required | Description |
|:---|:---|:---:|:---|
| `query` | string | ✅ | Natural language search query |
| `project` | string | — | Filter by project |
| `top_k` | integer | — | Number of results (default: 5) |

### `cortex_compliance_report`

**Parameters:** None.

Returns a structured compliance report with:
- Compliance score (0-5)
- Per-article requirement status
- Evidence references
- Recommendations

---

## Privacy Shield

The MCP server includes the **Privacy Shield** — an ingress guard that scans all incoming data for secrets before storage:

- GitHub tokens (`ghp_`, `gho_`, `ghs_`)
- GitLab PATs (`glpat-`)
- JWT tokens
- SSH private keys
- Slack tokens (`xoxb-`, `xoxp-`)
- AWS credentials
- Generic API keys
- And 4 more patterns

If a secret is detected, the fact is flagged and the agent is notified. Critical secrets (private keys) force local-only storage regardless of configuration.

---

## Google ADK Integration

CORTEX also integrates with **Google Agent Developer Kit (ADK)**:

```bash
pip install cortex-memory[adk]
cortex-adk  # Start the ADK runner
```

This provides the same trust tools via the Google ADK toolbox bridge.

---

## Toolbox Bridge

For environments that use the Toolbox protocol:

```python
from cortex.mcp.toolbox_bridge import get_toolbox_tools

tools = get_toolbox_tools()
# Returns a list of tool definitions compatible with the Toolbox protocol
```
