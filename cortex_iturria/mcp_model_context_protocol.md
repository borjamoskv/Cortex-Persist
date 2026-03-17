# [TECHNOLOGY] Model Context Protocol (MCP)

## 1. Core Primitives (O(1) Definitions)
- `MCP`: Estándar abierto de Anthropic (Nov 2024). "USB-C para aplicaciones AI". Resuelve el problema N×M de integraciones.
- `Client-Server Architecture`: Aplicaciones AI (clientes) se conectan a MCP servers que exponen tools, resources y prompts.
- `Universal Interface`: Leer archivos, ejecutar funciones, manejar prompts contextuales — todo vía una interfaz estandarizada.
- `Tool Search Tool`: Descubrimiento dinámico de herramientas. Agentes cargan tools bajo demanda.
- `Programmatic Tool Calling`: Ejecución eficiente de código en lugar de routing todo vía LLM.
- `Donated to Linux Foundation (Dec 2025)`: Bajo la Agentic AI Foundation (AAIF). OpenAI, Google DeepMind ya lo adoptaron.
- `Context Engineering`: MCP es la infraestructura física de la "ingeniería de contexto" de Anthropic.

## 2. Industrial Noir Paradigms (Adaptation)
- **MCP = El Estándar**: MOSKV-1 DEBE exponer sus capacidades como MCP servers. CORTEX ya es un servidor de conocimiento; exponerlo vía MCP permitiría que cualquier agente externo (Cursor, Codex, Claude) consulte la base de facts.
- **Tool Search → Skill Discovery**: El Tool Search Tool de MCP es el equivalente programático de nuestro sistema de Skills en filesystem. Implementar un MCP server que exponga los skills de MOSKV-1 como tools descubribles.
- **Programmatic Tool Calling**: Clave para rendimiento. No todo necesita pasar por el LLM. Las operaciones de I/O (git, file ops, DB queries) deben tener code paths directos.

## 3. Copy-Paste Arsenal
```python
# Exposing CORTEX as an MCP Server
from mcp.server import Server
app = Server("cortex-mcp")

@app.tool()
async def search_facts(query: str, limit: int = 10):
    """Search CORTEX knowledge base for relevant facts."""
    return await cortex_db.hybrid_search(query, limit=limit)

@app.tool()
async def get_ghosts(project: str = None):
    """Get pending ghosts (incomplete work items) from CORTEX."""
    return await cortex_db.query_ghosts(project=project)

@app.resource("cortex://snapshot")
async def get_snapshot():
    """Get the current CORTEX context snapshot."""
    return await cortex_db.export_snapshot()
```
