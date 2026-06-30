# [C5-REAL] Exergy-Maximized
"""
Embedding provider registry.
Decouples EmbeddingManager from hardcoded embedder implementations.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from babylon60.embeddings.provider import EmbeddingProvider

logger = logging.getLogger("cortex.embeddings.registry")

_EMBEDDING_PROVIDERS: dict[str, Callable[..., EmbeddingProvider]] = {}

def register_provider(name: str, factory: Callable[..., EmbeddingProvider]) -> None:
    """Register an embedding provider factory under a specific name."""
    _EMBEDDING_PROVIDERS[name] = factory
    logger.debug("Registered embedding provider: %s", name)

def get_provider(name: str, **kwargs: Any) -> EmbeddingProvider:
    """Instantiate and return a provider by name."""
    if name not in _EMBEDDING_PROVIDERS:
        raise ValueError(f"Unknown embedding provider: {name}. Available: {list(_EMBEDDING_PROVIDERS.keys())}")
    
    return _EMBEDDING_PROVIDERS[name](**kwargs)

# === Built-in Provider Factories ===

def _local_embedder_factory(**kwargs: Any) -> EmbeddingProvider:
    from babylon60.embeddings.local import LocalEmbedder
    return LocalEmbedder()

def _api_embedder_factory(**kwargs: Any) -> EmbeddingProvider:
    from babylon60.core import config
    from babylon60.embeddings.api_embedder import APIEmbedder
    
    provider = kwargs.get("provider", config.EMBEDDINGS_PROVIDER)
    target_dimension = kwargs.get("target_dimension", config.EMBEDDINGS_DIMENSION)
    task_type = kwargs.get("task_type", config.EMBEDDINGS_TASK_TYPE)
    
    return APIEmbedder(
        provider=provider,
        target_dimension=target_dimension,
        task_type=task_type
    )

def _null_embedder_factory(**kwargs: Any) -> EmbeddingProvider:
    from babylon60.embeddings.provider import NullEmbeddingProvider
    return NullEmbeddingProvider() # type: ignore

# Register standard providers
register_provider("local", _local_embedder_factory)
register_provider("api", _api_embedder_factory)
register_provider("null", _null_embedder_factory)
