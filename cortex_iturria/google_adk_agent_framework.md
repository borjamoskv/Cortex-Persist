# [TECHNOLOGY] Google ADK (Agent Development Kit)

## 1. Core Primitives (O(1) Definitions)
- `ADK`: Framework open-source de Google para construir agentes y sistemas multi-agente. Mismo framework usado internamente por Agentspace y Google CES.
- `Agent Hierarchy`: Arquitectura en árbol con relaciones padre-hijo. `SequentialAgent`, `ParallelAgent` y `LoopAgent` para orquestar flujos automatizados multi-paso.
- `Tool Ecosystem`: Agentes equipados con tools pre-built (Search, Code Exec), MCP tools, LangChain/LlamaIndex, y otros agentes como herramientas.
- `Model Agnostic`: Compatible con Gemini, Anthropic, Meta, Mistral vía Vertex AI Model Garden o LiteLLM.
- `Feb 2026 Update`: ADK reenmarcado como un "agent execution framework" con conexiones directas a GitHub, Jira, MongoDB y plataformas de observabilidad.

## 2. Industrial Noir Paradigms (Adaptation)
- **Workflow Agents nativos**: Los `SequentialAgent`, `ParallelAgent` y `LoopAgent` son réplicas exactas de los patrones que LEGION-1 implementa manualmente. MOSKV-1 debería evaluar si adoptar ADK como runtime base en lugar de reimplementar orquestación.
- **Agents-as-Tools**: ADK permite usar un agente como herramienta de otro agente. Este patrón es la base de la delegación fractal en LEGION-1.
- **MCP Integration nativa**: ADK ya soporta MCP servers, alineando el ecosistema con el estándar de la industria.

## 3. Copy-Paste Arsenal
```python
# ADK-style Agent Hierarchy (MOSKV-1 adaptation)
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

pipeline = SequentialAgent(
    name="josu_night_shift",
    sub_agents=[
        ParallelAgent(name="research", sub_agents=[lit_review, data_extract]),
        LoopAgent(name="iterate_tests", sub_agent=test_runner, max_iterations=10),
        code_reviewer
    ]
)
```
