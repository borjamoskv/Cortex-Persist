# cortex-mcp

> **CORTEX is long-term memory for MCP agents. Local, private, searchable, and available across sessions.**

Your AI remembers what happened yesterday.

- **Install:** 10 seconds
- **First stored fact:** < 60 seconds
- **Search latency:** < 20ms
- **Runs locally**
- **No cloud account**

## Quickstart (60 Seconds)

```bash
uvx cortex-mcp
```

Or add it to your Cursor/Windsurf/Claude configuration:

```json
{
  "mcpServers": {
    "cortex": {
      "command": "uvx",
      "args": ["cortex-mcp"]
    }
  }
}
```

### Try it out
1. **You:** "Remember that our backend uses FastAPI and SQLite."
2. *(Cursor invokes `cortex_store` in the background).*
3. **[New Session, next day] You:** "What backend stack are we using?"
4. *(Cursor invokes `cortex_search` and answers instantly).*

## Why CORTEX instead of Markdown files?

| Markdown | CORTEX |
| --- | --- |
| Búsqueda literal | Búsqueda semántica híbrida (embeddings) |
| Sin ranking | Ranking por relevancia (score < 20ms) |
| Sin contexto | Recuperación contextual acoplada a MCP |
| Manual | Integrado automáticamente en el IDE |
| No estructurado | Hechos indexados con metadatos |

## Core API
- `cortex_store`
- `cortex_search`
- `cortex_status`

*Private. Local. Zero setup.*
