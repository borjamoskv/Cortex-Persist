# epigenetic_memory.py
"""Epigenetic Memory module.

Implements a vector store wrapper that attaches an *emotion weight* to each
embedding. The weight influences retrieval: high‑pain (negative) memories are
penalised, positive memories are boosted. This mimics the "memory epigenetics"
concept from the design document.

The implementation uses a simple in‑memory dictionary for demonstration. In a
real system you would plug in a persistent vector DB (FAISS, Milvus, etc.).
"""

from __future__ import annotations
import datetime
import hashlib
from typing import Any, Dict, List, Tuple


class EpigeneticMemory:
    """Store embeddings with an emotional weight and provide biased retrieval.

    *emotion_weight* is a float in the range ``[-1.0, 1.0]`` where negative values
    represent painful or error‑inducing experiences and positive values represent
    rewarding experiences.
    """

    def __init__(self) -> None:
        # Internal store: id -> (embedding, metadata)
        self._store: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}

    # ---------------------------------------------------------------------
    def _hash(self, content: str) -> str:
        """Deterministic identifier based on content hash."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # ---------------------------------------------------------------------
    def upsert(self, content: str, embedding: List[float], emotion_weight: float) -> None:
        """Insert or update a memory entry.

        Parameters
        ----------
        content: str
            Original text or data that the embedding represents.
        embedding: List[float]
            Vector representation (e.g., from a sentence transformer).
        emotion_weight: float
            ``-1.0`` (max pain) → ``1.0`` (max reward).
        """
        if not -1.0 <= emotion_weight <= 1.0:
            raise ValueError("emotion_weight must be between -1.0 and 1.0")
        mem_id = self._hash(content)
        self._store[mem_id] = (
            embedding,
            {
                "content": content,
                "emotion_weight": emotion_weight,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )

    # ---------------------------------------------------------------------
    def retrieve(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Return the top‑k most relevant memories, re‑ranked by emotion.

        The base relevance is a simple dot‑product similarity. After sorting by
        similarity we apply a bias: painful memories (negative weight) are
        multiplied by ``0.1`` to make them almost invisible, while rewarding
        memories are amplified by ``2.0``.
        """
        # Compute raw similarity (dot product) – naive O(N) loop for demo.
        scores: List[Tuple[str, float]] = []
        for mem_id, (vec, meta) in self._store.items():
            # dot product
            sim = sum(a * b for a, b in zip(vec, query_embedding))
            scores.append((mem_id, sim))
        # Sort by similarity descending
        scores.sort(key=lambda x: x[1], reverse=True)

        results: List[Dict[str, Any]] = []
        for mem_id, base_score in scores[: top_k * 3]:  # fetch extra for re‑rank
            vec, meta = self._store[mem_id]
            ew = meta["emotion_weight"]
            # Apply emotional bias
            if ew < -0.5:
                biased_score = base_score * 0.1
            elif ew > 0.5:
                biased_score = base_score * 2.0
            else:
                biased_score = base_score
            results.append({"id": mem_id, "content": meta["content"], "emotion_weight": ew, "score": biased_score})
        # Final sort after bias
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # ---------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """Serialisable snapshot of the memory store (metadata only)."""
        return {mid: {"emotion_weight": meta["emotion_weight"], "timestamp": meta["timestamp"]} for mid, (_, meta) in self._store.items()}

# Example usage (remove before production)
if __name__ == "__main__":
    mem = EpigeneticMemory()
    mem.upsert("Found a bug in the auth flow", [0.1, 0.2, 0.3], -0.9)
    mem.upsert("Successfully deployed new version", [0.4, 0.5, 0.6], 0.8)
    query = [0.15, 0.25, 0.35]
    print(mem.retrieve(query))
```
