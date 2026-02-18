"""Embedding Sovereign Layer — EmbeddingManager for CORTEX."""

from __future__ import annotations

import logging

from cortex.embeddings import LocalEmbedder

logger = logging.getLogger("cortex.embeddings.manager")


class EmbeddingManager:
    """Manages the generation and lifecycle of embeddings."""

    def __init__(self, engine):
        self.engine = engine
        self._embedder = None

    def _get_embedder(self) -> LocalEmbedder:
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Generate embedding for a single text or batch."""
        return self._get_embedder().embed(text)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return self._get_embedder().embed_batch(texts, batch_size=batch_size)
