import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
    messages: list[dict[str, Any]] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
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
        async def node_wrapper(state: NightShiftState | dict[str, Any]) -> dict[str, Any]:
            logger.info("🔄 [SUPERVISOR] Ejecutando nodo: %s", node.name)
            current = (
                state
                if isinstance(state, NightShiftState)
                else NightShiftState.model_validate(state)
            )
            result = await node.execute(current)
            return result.model_dump()

        self.graph_builder.add_node(node.name, node_wrapper)

    def add_edge(self, source: str, target: str):
        """Define una arista incondicional."""
        self.graph_builder.add_edge(source, target)

    def add_conditional_edges(self, source: str, decision_func, edge_map: dict[str, str]):
        """Define bifurcación predictible."""
        self.graph_builder.add_conditional_edges(source, decision_func, edge_map)  # type: ignore  # pyright: ignore

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
        current = initial_state.model_copy(deep=True)
        try:
            async for state_update in self.compiled_app.astream(initial_state.model_dump()):  # type: ignore
                current = self._merge_state_update(current, state_update)
                yield current
        except (ValueError, TypeError, RuntimeError) as e:
            logger.error("☠️ [SUPERVISOR] Fallo de Ejecución Duradera: %s", e)
            raise LangGraphSupervisorError(f"Colapso en grafo: {e}") from e

    @staticmethod
    def _merge_state_update(
        current: NightShiftState,
        state_update: NightShiftState | dict[str, Any],
    ) -> NightShiftState:
        """Normalize LangGraph version-specific stream chunks into full state."""
        if isinstance(state_update, NightShiftState):
            return state_update
        if not isinstance(state_update, dict):
            return current

        values = state_update.values() if any(isinstance(v, dict) for v in state_update.values()) else [state_update]
        merged = current.model_dump()
        for value in values:
            if isinstance(value, NightShiftState):
                merged.update(value.model_dump())
            elif isinstance(value, dict):
                if "variables" in value and isinstance(value["variables"], dict):
                    variables = dict(merged.get("variables", {}))
                    variables.update(value["variables"])
                    merged["variables"] = variables
                if "messages" in value and isinstance(value["messages"], list):
                    merged["messages"] = value["messages"]
                for key in ("session_id", "next_node", "retry_count", "max_retries", "is_paused"):
                    if key in value:
                        merged[key] = value[key]
        return NightShiftState.model_validate(merged)
