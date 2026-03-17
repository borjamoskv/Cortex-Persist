# [TECHNOLOGY] Microsoft AutoGen

## 1. Core Primitives (O(1) Definitions)
- `Async Event-Driven Architecture (v0.4)`: Rediseño total en 2025. Modular, extensible, escalable. Componentes pluggables (agents, tools, memory, models).
- `AutoGen Studio`: Herramienta low-code drag-and-drop para construir workflows multi-agente visualmente.
- `Cross-Language Support`: Interoperabilidad Python ↔ .NET para agentes construidos en distintos lenguajes.
- `OpenTelemetry Integration`: Observabilidad de grado industrial para tracking y debugging de interacciones entre agentes.
- `MCP Integration nativa`: Soporte built-in para MCP servers.
- `Semantic Kernel Alignment`: Runtime alineado con Semantic Kernel de Microsoft para soluciones enterprise multi-agente.
- `Azure Integration`: Azure OpenAI, Cognitive Search, Form Recognizer como herramientas nativas de los agentes.

## 2. Industrial Noir Paradigms (Adaptation)
- **Event-Driven = Proactividad**: La arquitectura event-driven de AutoGen es exactamente lo que necesita MOSKV-Josu: reaccionar a eventos (commit en Git, inactividad del usuario, test fallido) sin polling constante.
- **AutoGen Studio ≈ Agent Spawner Visual HQ**: El concepto de construir workflows visualmente está alineado con el Agent Spawner Visual HQ de Live Notch.
- **OpenTelemetry**: CORTEX debería adoptar OpenTelemetry como capa de observabilidad para los ciclos de Josu Night Shift.

## 3. Copy-Paste Arsenal
```python
# AutoGen v0.4 Event-Driven Pattern
from autogen_core import SingleThreadedAgentRuntime
runtime = SingleThreadedAgentRuntime()
# Register agents with event handlers
await runtime.register("planner", PlannerAgent)
await runtime.register("executor", ExecutorAgent)
# Agents communicate via async message passing
await runtime.send_message(TaskMessage(content="Build REST API"), recipient="planner")
await runtime.run_until_idle()
```
