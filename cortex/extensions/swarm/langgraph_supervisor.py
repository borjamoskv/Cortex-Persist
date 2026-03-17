from __future__ import annotations
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel, ConfigDict

try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    StateGraph = None
    END = None
    LANGGRAPH_AVAILABLE = False

logger = logging.getLogger("cortex.extensions.swarm.supervisor")


class NightShiftState(BaseModel):
    """Estado persistente para ejecución duradera (Agent State)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str
    messages: list[dict[str, Any]] = []
    variables: dict[str, Any] = {}
    next_node: str = "planner"
    retry_count: int = 0
    max_retries: int = 3
    is_paused: bool = False

    @classmethod
    def create(cls, session_id: str | None = None):
        return cls(session_id=session_id or str(uuid.uuid4()))


class SupervisorNode:
    """Clase base para Nodos de LangGraph."""

    def __init__(self, name: str):
        self.name = name

    async def execute(self, state: NightShiftState) -> NightShiftState:
        """La mutación del estado O(1)."""
        raise NotImplementedError


class LangGraphSupervisorError(Exception):
    pass


class CortexLangGraphSupervisor:
    """
    Supervisor O(1) de LangGraph adaptado para CORTEX persistency.
    Implementa el paradigma "Night Shift": Durable Execution & Human-in-the-Loop.
    """

    def __init__(self, name: str = "cortex-swarm-supervisor"):
        if not LANGGRAPH_AVAILABLE:
            raise LangGraphSupervisorError(
                "LangGraph no está instalado. Ejecute 'pip install langgraph'."
            )

        self.name = name
        self.nodes: dict[str, SupervisorNode] = {}
        self.graph_builder = StateGraph(NightShiftState)  # type: ignore[reportOptionalCall]
        self.compiled_app = None

    def add_node(self, node: SupervisorNode):
        """Añade un nodo al grafo."""
        self.nodes[node.name] = node

        # Envolvermos el async `execute` para adaptarlo a LangGraph
        async def node_wrapper(state: NightShiftState) -> NightShiftState:
            logger.info("🔄 [SUPERVISOR] Ejecutando nodo: %s", node.name)
            return await node.execute(state)

        self.graph_builder.add_node(node.name, node_wrapper)

    def add_edge(self, source: str, target: str):
        """Define una arista incondicional."""
        self.graph_builder.add_edge(source, target)

    def add_conditional_edges(self, source: str, decision_func, edge_map: dict[str, str]):
        """Define bifurcación predictible."""
        self.graph_builder.add_conditional_edges(source, decision_func, edge_map)

    def compile(self, checkpointer=None):
        """Compila la aplicación en un DAG O(1)."""
        self.compiled_app = self.graph_builder.compile(checkpointer=checkpointer)
        return self.compiled_app

    async def stream_execution(
        self, initial_state: NightShiftState
    ) -> AsyncGenerator[NightShiftState, None]:
        """Arranca el enjambre y cede estado por cada tick de progreso."""
        if not self.compiled_app:
            self.compile()

        logger.info("🚀 [SUPERVISOR] Lanzando Night Shift (Session: %s)", initial_state.session_id)
        # En la API real de langgraph (langgraph>=0.0.x), astream funciona diferente dependiendo de la versión
        # Pero mockearemos este flujo para compatibilidad.
        try:
            # LangGraph astream returns chunks of updates
            async for state_update in self.compiled_app.astream(initial_state):  # type: ignore[reportOptionalMemberAccess]
                yield state_update
        except (ValueError, TypeError, RuntimeError) as e:
            logger.error("☠️ [SUPERVISOR] Fallo de Ejecución Duradera: %s", e)
            raise LangGraphSupervisorError(f"Colapso en grafo: {e}") from e
