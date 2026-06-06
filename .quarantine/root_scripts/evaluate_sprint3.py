# [C5-REAL] Exergy-Maximized
import sys
import asyncio

from cortex.engine import CortexEngine
from cortex.interfaces.memory_provider import MemoryProvider, MemoryNode, MemorySubgraph
from cortex.pipeline.triage import SemanticAttentionOrchestrator
import numpy as np


class CortexSMEProvider(MemoryProvider):
    def __init__(self, engine: CortexEngine):
        self.engine = engine
        self._loop = asyncio.get_event_loop()

    def embed(self, text: str) -> np.ndarray | list[float]:
        # Get embedder from engine
        embedder = self.engine._get_embedder()
        return embedder.embed(text)

    def search(self, query: str, limit: int = 10) -> list[MemoryNode]:
        # Not used by hybrid retriever directly, but required by interface
        return []

    def vector_search(
        self, embedding: np.ndarray | list[float], limit: int = 50
    ) -> list[MemoryNode]:
        # Using CortexEngine's hybrid_search internally via search, but we must pass the embedding
        results = self._loop.run_until_complete(
            self.engine.search(query="", top_k=limit)  # We might need a real vector search method
        )
        nodes = []
        for r in results or []:
            nodes.append(
                MemoryNode(
                    id=str(getattr(r, "id", "unknown")),
                    embedding=getattr(r, "embedding", embedding),  # Mocked if missing
                    fact_type=getattr(r, "fact_type", getattr(r, "type", "knowledge")),
                    timestamp=0.0,
                    causal_links=[],
                    semantic_tags=[],
                )
            )
        return nodes

    def neighbors(self, node_id: str) -> list[MemoryNode]:
        # Mocked graph edges for testing traversal
        return []

    def causal_edges(self, node_id: str) -> list[tuple[str, str, float]]:
        # Mocked causal edges
        return []

    def hydrate(self, nodes: list[MemoryNode]) -> list[MemoryNode]:
        hydrated = []
        for node in nodes:
            try:
                fact = self._loop.run_until_complete(self.engine.get_fact(int(node.id)))
                if fact:
                    node.content = fact.content
                else:
                    node.content = "<Fact not found>"
            except Exception as e:
                node.content = f"<Decryption/Fetch Error: {e}>"
            hydrated.append(node)
        return hydrated


async def setup_engine() -> CortexEngine:
    engine = CortexEngine("/tmp/cortex_copy.db")
    await engine.init_db()
    return engine


def main():
    queries = ["por qué falló el sistema ayer", "relación entre X y Y", "cosas sobre gatos"]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    engine = loop.run_until_complete(setup_engine())

    provider = CortexSMEProvider(engine)

    # We will just run the IntentEncoder and HybridRetriever manually for these test queries,
    # because SemanticAttentionOrchestrator takes a GitHub URL, and these are raw queries.
    from cortex.semantic.intent_encoder import IntentEncoder
    from cortex.semantic.hybrid_retriever import HybridRetriever

    intent_encoder = IntentEncoder(provider)
    retriever = HybridRetriever(provider)

    for q in queries:
        print(f"\n[{q}]")
        try:
            intent = intent_encoder.encode(q)
            print(
                f"Intent -> Temporal Bias: {intent.temporal_bias}, Abstraction: {intent.abstraction_level}"
            )

            subgraph = retriever.retrieve(query=q, intent=intent, k=10)
            print(f"Subgraph Coherence Score: {subgraph.coherence_score:.2f}")
            print(f"Nodes in Subgraph: {len(subgraph.nodes)}")
            print(f"Edges in Subgraph: {len(subgraph.edges)}")

            for i, node in enumerate(subgraph.nodes):
                print(
                    f"  [{i + 1}] Node ID: {node.id} | Type: {node.fact_type} | Content: {node.content[:60]}..."
                )

        except Exception as e:
            print(f"FAILED: {e}")

    loop.run_until_complete(engine.close())


if __name__ == "__main__":
    main()
