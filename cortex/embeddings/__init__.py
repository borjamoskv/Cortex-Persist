"""CORTEX v5.0 — Embeddings.

Vector substrate for semantic memory and similarity search.
"""

from __future__ import annotations

from cortex.embeddings.local import _DEVICE, EMBEDDING_DIM, LocalEmbedder, _resolve_device
from cortex.embeddings.manager import EmbeddingManager
from cortex.embeddings.provider import EmbeddingProvider

__all__ = [
    "EMBEDDING_DIM",
    "EmbeddingManager",
    "EmbeddingProvider",
    "LocalEmbedder",
    "_DEVICE",
    "_resolve_device",
]

# Wave 6: Default dimensions for standard CORTEX memory
DEFAULT_DIMENSIONS = 384
SPECULAR_DIMENSIONS = 8000
