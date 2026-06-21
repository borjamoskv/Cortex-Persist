# [C5-REAL] Exergy-Maximized
"""Embeddings.

Vector substrate for semantic memory and similarity search.
"""

from __future__ import annotations

from cortex.embeddings import local as _local
from cortex.embeddings.manager import EmbeddingManager
from cortex.embeddings.provider import EmbeddingProvider

_DEVICE = _local._DEVICE
EMBEDDING_DIM = _local.EMBEDDING_DIM
LocalEmbedder = _local.LocalEmbedder


def _resolve_device() -> str:
    """Resolve the device using the package-level override when present."""
    if _DEVICE != "auto":
        return _DEVICE
    return _local._resolve_device()


__all__ = [
    "EMBEDDING_DIM",
    "_DEVICE",
    "EmbeddingManager",
    "EmbeddingProvider",
    "LocalEmbedder",
    "_resolve_device",
]

# Wave 6: Default dimensions for standard CORTEX memory
DEFAULT_DIMENSIONS = 384
SPECULAR_DIMENSIONS = 8000
