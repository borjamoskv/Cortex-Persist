# [TECHNOLOGY] LangGraph Multi-Agent Architecture

## 1. Core Primitives (O(1) Definitions)
- `Graph-Based Workflows`: Workflows como grafos dirigidos. Nodos = agentes/tools/pasos. Aristas = flujo de operaciones. Permite ejecución condicional, paralela y control explícito.
- `State Management`: Estado compartido y persistente a través de workflows. Los agentes recuerdan contexto entre interacciones y se adaptan dinámicamente.
- `Agent Supervisor Pattern`: Un agente central rutea tareas a sub-agentes especializados. Los nodos pueden ser otros grafos LangGraph (composición jerárquica).
- `Durable Execution`: Agentes que persisten a través de fallos y corren por periodos extendidos.
- `Human-in-the-Loop nativo`: Pausa la ejecución para revisión humana o modificación del estado del agente.

## 2. Industrial Noir Paradigms (Adaptation)
- **State Machine vs Free-Form**: LangGraph ofrece más predictibilidad que AutoGen (conversaciones autónomas libres). Para MOSKV-Josu (Night Shift), la predictibilidad de una state machine es OBLIGATORIA.
- **Durable Execution**: Exactamente lo que necesita Josu para sobrevivir crashes a mitad de la noche sin perder progreso.
- **Composición Jerárquica**: Un grafo que contiene otros grafos = LEGION-1 nativo. Cada sub-grafo es un mini-enjambre autónomo.

## 3. Copy-Paste Arsenal
```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_agent)
workflow.add_node("executor", executor_agent)
workflow.add_node("critic", critic_agent)
workflow.add_edge("planner", "executor")
workflow.add_conditional_edges("executor", should_retry, {"retry": "executor", "review": "critic"})
workflow.add_edge("critic", END)
app = workflow.compile()
```
