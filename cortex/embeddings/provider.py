"""
Embedding providers - Abstraction layer for survival-ready embeddings.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger("cortex")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    def is_available(self) -> bool:
        """Check if the provider is available in the current environment."""
        ...

    def embed(self, text: str) -> list[float]:
        """Generate an embedding for the given text."""
        ...


class NullEmbeddingProvider:
    """survival-ready provider that does nothing. (Axiom Ω₃)"""

    def is_available(self) -> bool:
        return True

    def embed(self, text: str) -> list[float]:
        logger.debug("NullEmbeddingProvider: ignoring request for '%s'", text[:20])
        return []


class TorchEmbeddingProvider:
    """Legacy provider using LocalEmbedder (depends on torch)."""

    def __init__(self, embedder: any):
        self._embedder = embedder

    def is_available(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available() or torch.backends.mps.is_available() or True
        except ImportError:
            return False

    def embed(self, text: str) -> list[float]:
        return self._embedder.embed(text)
