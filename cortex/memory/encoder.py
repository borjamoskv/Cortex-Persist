"""
CORTEX v5.2 — Async Embedding Encoder.

Wraps the existing LocalEmbedder in asyncio.to_thread() to guarantee
event-loop immunity for CPU-bound ML inference.

The model is loaded lazily on first use and cached for the process lifetime.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from cortex.embeddings import EMBEDDING_DIM, LocalEmbedder

__all__ = ["AsyncEncoder"]

logger = logging.getLogger("cortex.memory.encoder")


class AsyncEncoder:
    """Event-loop-safe async wrapper around LocalEmbedder.

    All encoding happens in a background thread via asyncio.to_thread(),
    ensuring the FastAPI / daemon event loop is never blocked by
    CPU-bound SentenceTransformer inference.
    """

    __slots__ = ("_embedder",)

    def __init__(self, embedder: Optional[LocalEmbedder] = None) -> None:
        self._embedder = embedder or LocalEmbedder()

    async def encode(self, text: str) -> list[float]:
        """Encode a single text to a 384-dim vector (async, thread-isolated)."""
        return await asyncio.to_thread(self._embedder.embed, text)  # type: ignore[reportReturnType]

    async def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts (async, thread-isolated)."""
        if not texts:
            return []
        return await asyncio.to_thread(self._embedder.embed_batch, texts)

    @property
    def dimension(self) -> int:
        """Embedding dimension (384 for all-MiniLM-L6-v2)."""
        return EMBEDDING_DIM

    @property
    def model_identity_hash(self) -> str:
        """SHA-256 identity hash of the underlying embedding model.

        Used to version TopologicalAnchors — if this changes,
        reference signatures are invalid and must be recalculated cold.
        """
        return self._embedder.model_identity_hash
