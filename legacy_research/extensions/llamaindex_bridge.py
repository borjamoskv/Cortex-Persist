# [C5-REAL] Exergy-Maximized
from typing import Any

from llama_index.core.callbacks.base_handler import (
    BaseCallbackHandler,  # pyright: ignore[reportMissingImports]
)
from llama_index.core.callbacks.schema import CBEventType  # pyright: ignore[reportMissingImports]
from llama_index.core.postprocessor.types import (
    BaseNodePostprocessor,  # pyright: ignore[reportMissingImports]
)
from llama_index.core.schema import NodeWithScore  # pyright: ignore[reportMissingImports]
from pydantic import Field

from cortex.engine import CortexEngine


class ExergyFilter(BaseNodePostprocessor):
    """
    C5-REAL Exergy Filter for RAG nodes.
    Aniquila la entropía (nodos basura) antes de que contaminen la inferencia.
    "Elegir es CERRAR puertas."
    """

    min_exergy: float = Field(
        default=0.75, description="Mínima exergía requerida para sobrevivir al filtro."
    )

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: Any | None = None
    ) -> list[NodeWithScore]:
        exergic_nodes = []
        for n in nodes:
            # Score de similitud como proxy termodinámico (Exergía = Trabajo Útil)
            score = n.score if n.score is not None else 0.0
            if score >= self.min_exergy:
                exergic_nodes.append(n)
        return exergic_nodes


class CortexIndexCallback(BaseCallbackHandler):
    """
    C5-REAL Cryptographic tracing of LlamaIndex RAG retrieval paths.
    """

    def __init__(self, engine: CortexEngine, agent_id: str):
        super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
        self.engine = engine
        self.agent_id = agent_id

    def on_event_start(
        self,
        event_type: CBEventType,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        return event_id

    def on_event_end(
        self,
        event_type: CBEventType,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        if payload is None:
            payload = {}
        if event_type == CBEventType.RETRIEVE:
            nodes = payload.get("nodes", [])

            # Cómputo termodinámico: calcular la exergía media del retrieval
            total_nodes = len(nodes)
            avg_exergy = 0.0
            if total_nodes > 0:
                scores = [n.score for n in nodes if hasattr(n, "score") and n.score is not None]
                if scores:
                    avg_exergy = sum(scores) / len(scores)

            sources = [
                n.node.node_id for n in nodes if hasattr(n, "node") and hasattr(n.node, "node_id")
            ]
            self.engine.store_sync(
                fact_type="rag_retrieve",
                content=f"RETRIEVAL_EVENT: Fetched {len(sources)} nodes | Avg Exergy: {avg_exergy:.4f}",
                metadata={"nodes": sources, "event": "rag_retrieve", "avg_exergy": avg_exergy},
                agent_id=self.agent_id,
            )

    def start_trace(self, trace_id: str | None = None) -> None:
        pass

    def end_trace(
        self,
        trace_id: str | None = None,
        trace_map: dict[str, list[str]] | None = None,
    ) -> None:
        pass
