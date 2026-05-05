# MCP Server

CORTEX implements the **Model Context Protocol (MCP)** for IDE and agent integrations.

For product adoption, the recommended minimum is simple: use the MCP server when another tool needs
remote access to the same verifiable-memory surface you already use through the CLI or Python API.

---

## Install

```bash
pip install "cortex-persist[mcp]"
```

If you already installed the base package without extras, you can also install the MCP SDK
directly with:

```bash
pip install mcp
```

---

## Start The MCP Server

```bash
python -m cortex.mcp
```

Or explicitly:

```bash
python -m cortex.mcp.server
```

The default transport is stdio, which is what most IDE integrations expect.

By default, the server starts with the minimal core toolset only. To expose broader MCP families
such as trace, trust/compliance, health, or operator/runtime tooling, set
`CORTEX_ENABLE_EXPERIMENTAL_MCP=1` before launch.

For an SSE transport, the experimental CLI exposes:

```bash
CORTEX_ENABLE_EXPERIMENTAL_CLI=1 \
cortex mcp trust --transport sse --port 5002
```

The default documented launch path remains stdio via `python -m cortex.mcp`.

---

## Compatible IDEs

| IDE | Status |
| :--- | :--- |
| Claude Code | Native |
| Cursor | Native |
| OpenClaw | Native |
| Windsurf | Native |
| Antigravity | Native |

---

## Recommended Core Tools

| Tool | Description |
| :--- | :--- |
| `cortex_store` | Store a fact with automatic hash chaining |
| `cortex_search` | Search persisted memory |
| `cortex_status` | System health, statistics, and database info |
| `cortex_ledger_verify` | Full ledger integrity check |

These four tools are enough for most IDE and agent integrations.

---

## Extended Tool Families

When `CORTEX_ENABLE_EXPERIMENTAL_MCP=1`, the MCP server also registers broader tool families for
trust/compliance, traceability, embedding, health, genesis, and operator workflows. Common
examples include:

| Tool | Description |
| :--- | :--- |
| `cortex_verify_fact` | Cryptographic verification certificate for a single fact |
| `cortex_audit_trail` | Generate a timestamped, hash-verified audit log |
| `cortex_compliance_report` | EU AI Act Article 12 compliance snapshot with score |
| `cortex_decision_lineage` | Trace the lineage of a decision |

Adopt those only when the basic memory flow is already in place.

---

## Configuration

### Claude Code

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

### Cursor

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

### Antigravity

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

## Boundary Note

The MCP server can do more than the minimal memory flow, but the recommended product adoption path
is still:

1. `cortex_store`
2. `cortex_search`
3. `cortex_status`
4. `cortex_ledger_verify`
