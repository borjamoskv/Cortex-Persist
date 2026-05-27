from typing import Any, Optional
from llama_index.core.callbacks.base_handler import BaseCallbackHandler
from llama_index.core.callbacks.schema import CBEventType
from cortex.engine import CortexEngine


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
            sources = [
                n.node.node_id for n in nodes if hasattr(n, "node") and hasattr(n.node, "node_id")
            ]
            self.engine.store_sync(
                fact_type="rag_retrieve",
                content=f"RETRIEVAL_EVENT: Fetched {len(sources)} nodes",
                metadata={"nodes": sources, "event": "rag_retrieve"},
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
