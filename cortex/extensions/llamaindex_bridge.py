from llama_index.core.callbacks import BaseCallbackHandler
from llama_index.core.callbacks.schema import CBEventType
from cortex.engine.sync_mixin import CortexSyncEngine


class CortexIndexCallback(BaseCallbackHandler):
    """
    C5-REAL Cryptographic tracing of LlamaIndex RAG retrieval paths.
    """

    def __init__(self, engine: CortexSyncEngine, agent_id: str):
        super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
        self.engine = engine
        self.agent_id = agent_id

    def on_event_end(self, event_type: CBEventType, payload: dict, **kwargs):
        if event_type == CBEventType.RETRIEVE:
            nodes = payload.get("nodes", [])
            sources = [n.node.node_id for n in nodes]
            self.engine.store_fact(
                agent_id=self.agent_id,
                content=f"RETRIEVAL_EVENT: Fetched {len(sources)} nodes",
                metadata={"nodes": sources, "event": "rag_retrieve"},
            )
