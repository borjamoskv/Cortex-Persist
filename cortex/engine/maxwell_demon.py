# [C5-REAL] Exergy-Maximized
"""
Maxwell's Demon [Semantic Entropy Gating]
Implements semantic gating to purge redundant context chunks before LLM invocation.
Relies on LocalEmbedder (MiniLM) to compute semantic similarity and filter noise.
"""

import logging
import math
from typing import List

from cortex.embeddings.local import LocalEmbedder

logger = logging.getLogger(__name__)


class MaxwellDemon:
    """
    Semantic Entropy Gating Engine.
    Acts as a thermodynamic filter, discarding semantically redundant 
    information to maximize informational exergy and reduce context length.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Cosine similarity above which a chunk is considered redundant.
        """
        self.threshold = similarity_threshold
        self.embedder = LocalEmbedder()

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def purge_redundant(self, chunks: List[str]) -> List[str]:
        """
        Evaluates a sequence of text chunks and removes those that are semantically
        redundant with respect to the chunks already accepted.
        
        Args:
            chunks: List of text chunks (strings) to evaluate.
            
        Returns:
            List of non-redundant text chunks.
        """
        if not chunks:
            return []

        logger.info("[MaxwellDemon] Evaluando %d chunks para purga entrópica.", len(chunks))

        # Embed all chunks in a single batch for efficiency
        embeddings = self.embedder.embed_batch(chunks)

        accepted_chunks: List[str] = []
        accepted_embeddings: List[List[float]] = []

        purged_count = 0

        for chunk, emb in zip(chunks, embeddings):
            is_redundant = False

            # Compare against already accepted chunks
            for acc_emb in accepted_embeddings:
                sim = self._cosine_similarity(emb, acc_emb)
                if sim >= self.threshold:
                    is_redundant = True
                    break

            if not is_redundant:
                accepted_chunks.append(chunk)
                accepted_embeddings.append(emb)
            else:
                purged_count += 1

        logger.info(
            "[MaxwellDemon] Purga completada. Purgados: %d. Retenidos: %d.",
            purged_count,
            len(accepted_chunks)
        )
        return accepted_chunks
