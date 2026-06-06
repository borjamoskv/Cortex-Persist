<!-- [C5-REAL] Exergy-Maximized -->
# Persistent Memory for MCP Agents

> **CORTEX is long-term memory for MCP agents. Local, private, searchable, and available across sessions.**

Your AI remembers what happened yesterday.

Store facts.
Search context.
Continue work across sessions.

```bash
uvx cortex-mcp
```

### <30 second demo>
1. **You:** "Remember that our backend uses FastAPI and SQLite."
2. *(Cursor invokes `cortex_store` in the background).*
3. **[New Session, next day] You:** "What backend stack are we using?"
4. *(Cursor invokes `cortex_search` and answers instantly).*

### Works with:
- Cursor
- Claude Desktop
- Windsurf

### Why CORTEX instead of Markdown files?

| Markdown | CORTEX |
| --- | --- |
| Búsqueda literal | Búsqueda semántica híbrida (embeddings) |
| Sin ranking | Ranking por relevancia (score < 20ms) |
| Sin contexto | Recuperación contextual acoplada a MCP |
| Manual | Integrado automáticamente en el IDE |
| No estructurado | Hechos indexados con metadatos |

---

### API Core (Día 1)
Solo exponemos el valor inmediato:
- `cortex_store`
- `cortex_search`
- `cortex_status`

*Private. Local. Zero setup.*
