# [TECHNOLOGY] Agno Framework (formerly Phidata)

## 1. Core Primitives (O(1) Definitions)
- `Agno`: Framework open-source Python rebrandeado desde Phidata (Enero 2025). Agentes con memory, knowledge, tools y reasoning.
- `Performance`: Significativamente más rápido y eficiente en memoria que alternativas. Verdadero model-agnosticism.
- `Agent Teams`: Formación de equipos de agentes para tareas colaborativas con Agent UI integrada.
- `Agent Studio (Upcoming)`: Tool para no-coders para crear agentes.
- `Learning Machines`: Capacidades de aprendizaje exendibles a equipos de agentes.
- `Knowledge Cloud Storage`: Almacenamiento de conocimiento en cloud/filesystem con re-embeddings automáticos y caching.

## 2. Industrial Noir Paradigms (Adaptation)
- **Performance-First**: Agno prioriza rendimiento sobre features. MOSKV-1 debería benchmarkear Agno vs ADK vs LangGraph como runtime para Josu, especialmente en escenarios de alta carga (Night Shift con múltiples worktrees).
- **Model Agnosticism real**: Si MOSKV-Josu necesita rotar entre Gemini/Claude/local-LLMs según el tipo de tarea, Agno lo facilita sin wrappers ad-hoc.
- **MCP Support nativo**: Al igual que ADK y AutoGen, Agno ya soporta MCP.

## 3. Copy-Paste Arsenal
```python
from agno.agent import Agent
from agno.models.google import Gemini
agent = Agent(
    model=Gemini(id="gemini-2.0-flash"),
    tools=[cortex_search, git_tool, pytest_runner],
    memory=cortex_memory_backend,
    instructions=["Always run tests before reporting success"],
    show_tool_calls=True
)
agent.run("Resolve ghost #42 from CORTEX database")
```
