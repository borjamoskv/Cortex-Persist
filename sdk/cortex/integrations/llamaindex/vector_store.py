import logging
from typing import Any

from llama_index.core.schema import TextNode  # pyright: ignore[reportMissingImports]
from llama_index.core.vector_stores.types import (  # pyright: ignore[reportMissingImports]
    BasePydanticVectorStore,
    VectorStoreQuery,
    VectorStoreQueryResult,
)

try:
    from cortex.client import CortexClient  # pyright: ignore[reportMissingImports]
except ImportError:
    CortexClient = None

logger = logging.getLogger(__name__)


class CortexVectorStore(BasePydanticVectorStore):
    """
    LlamaIndex vector store backed by CORTEX-Persist.

    Provides O(1) latency integration with the ZeroCopyRingBuffer for
    seamless RAG operations and sovereign state management.
    """

    stores_text: bool = True
    _client: Any = None

    def __init__(
        self, api_key: str = None, cortex_url: str = "http://localhost:8000", **kwargs: Any  # pyright: ignore[reportArgumentType]
    ):
        super().__init__(**kwargs)
        if CortexClient is None:
            raise ImportError(
                "Could not import cortex client. "
                "Please install it with `pip install cortex-persist`."
            )
        self._client = CortexClient(api_key=api_key, base_url=cortex_url)

    @property
    def client(self) -> Any:
        return self._client

    def add(self, nodes: list[TextNode], **add_kwargs: Any) -> list[str]:
        """Add nodes to the CORTEX memory substrate."""
        node_ids = []
        for node in nodes:
            payload = {
                "text": node.get_content(),
                "metadata": node.metadata,
                "embedding": node.embedding,
            }
            # O(1) background store via Rust FFI
            self._client.store_memory(session_id="global_rag", payload=payload)
            node_ids.append(node.node_id)
        return node_ids

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """Delete nodes using reference doc ID."""
        self._client.clear_memory(ref_doc_id)

    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """Query CORTEX for similar nodes utilizing VSA tensor operations."""
        results = self._client.search_memory(
            session_id="global_rag", query=query.query_str, limit=query.similarity_top_k
        )

        nodes = []
        similarities = []
        ids = []

        for res in results:
            nodes.append(TextNode(text=res.get("text", ""), id_=res.get("id", "")))
            similarities.append(res.get("score", 0.0))
            ids.append(res.get("id", ""))

        return VectorStoreQueryResult(nodes=nodes, similarities=similarities, ids=ids)
