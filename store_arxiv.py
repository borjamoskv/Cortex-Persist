import asyncio

from cortex.engine import Cortex


async def main():
    cx = Cortex()

    # Wait for the DB to be ready if necessary

    axioms = [
        {
            "crystal_type": "discovery",
            "project": "cortex-memory",
            "source_url": "https://arxiv.org/abs/2504.19413",
            "confidence": 0.95,
            "source_title": "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory",
            "source_type": "arxiv",
            "chunk_idx": 16,
            "noise_ratio": 0.2,
            "published_date": "2025-04",
            "domain": "ai-agents-memory",
            "content": "Dense natural language memory (Mem0) achieves superior retrieval efficiency and accuracy for single-hop and multi-hop queries compared to graph-based memory (Mem0^g), which introduces redundancy and latency overhead during multi-step reasoning.",
        },
        {
            "crystal_type": "decision",
            "project": "cortex-memory",
            "source_url": "https://arxiv.org/abs/2504.19413",
            "confidence": 0.90,
            "source_title": "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory",
            "source_type": "arxiv",
            "chunk_idx": 18,
            "noise_ratio": 0.2,
            "published_date": "2025-04",
            "domain": "ai-agents-memory",
            "content": "Use flat natural language memory with selective embedding retrieval for production AI agents requiring low interactive latency, reserving graph memory (Mem0^g) exclusively for temporal traceability and open-domain queries.",
        },
        {
            "crystal_type": "discovery",
            "project": "cortex-memory",
            "source_url": "https://arxiv.org/abs/2504.19413",
            "confidence": 0.95,
            "source_title": "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory",
            "source_type": "arxiv",
            "chunk_idx": 21,
            "noise_ratio": 0.2,
            "published_date": "2025-04",
            "domain": "ai-agents-memory",
            "content": "Graph-based memory storage with local node summaries (e.g., Zep structure) can consume up to 20x more tokens than raw conversation context, causing write delays unsuitable for real-time applications.",
        },
        {
            "crystal_type": "discovery",
            "project": "cortex-memory",
            "source_url": "https://arxiv.org/abs/2504.19413",
            "confidence": 0.90,
            "source_title": "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory",
            "source_type": "arxiv",
            "chunk_idx": 9,
            "noise_ratio": 0.1,
            "published_date": "2025-04",
            "domain": "ai-agents-memory",
            "content": "An LLM (e.g., GPT-4o-mini) can directly decide CRUD operations (ADD, UPDATE, DELETE, NOOP) by iteratively comparing a new fact against the top-k similar facts from a vector store, maintaining knowledge base coherence without requiring intermediate classifiers.",
        },
    ]

    print("Starting ingestion...")
    for axiom in axioms:
        fact_id = await cx.store(
            type=axiom["crystal_type"],
            project=axiom["project"],
            source=f"autodidact-omega:{axiom['source_url']}",
            confidence=axiom["confidence"],
            meta={
                "source_title": axiom["source_title"],
                "source_type": axiom["source_type"],
                "chunk_position": axiom["chunk_idx"],
                "noise_ratio": axiom["noise_ratio"],
                "parent_axiom_ids": [],
                "temporal_marker": axiom["published_date"],
                "domain": axiom["domain"],
            },
            summary=axiom["content"],
        )
        print(f"Stored crystal '{axiom['crystal_type']}' with ID: {fact_id}")

    print("Ingestion complete.")


if __name__ == "__main__":
    asyncio.run(main())
