"""
CORTEX v5.2 — Async Embedding Encoder.

Wraps the existing LocalEmbedder in asyncio.to_thread() to guarantee
event-loop immunity for CPU-bound ML inference.

The model is loaded lazily on first use and cached for the process lifetime.
"""

from __future__ import annotations

import asyncio
import logging

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

    def __init__(self, embedder: LocalEmbedder | None = None) -> None:
        self._embedder = embedder or LocalEmbedder()

    async def encode(self, text: str) -> list[float]:
        """Encode a single text to a 384-dim vector (async, thread-isolated)."""
        return await asyncio.to_thread(self._embedder.embed, text)

    async def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts (async, thread-isolated)."""
        if not texts:
            return []
        return await asyncio.to_thread(self._embedder.embed_batch, texts)

    @property
    def dimension(self) -> int:
        """Embedding dimension (384 for all-MiniLM-L6-v2)."""
        return EMBEDDING_DIM
