"""
CORTEX v5.3 — BYOK Embedding Engine.

Wraps either the LocalEmbedder or an External Provider (OpenAI, Gemini)
based on Tenant configuration. Ensures SQLite-vec dimension compatibility.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Union

logger = logging.getLogger("cortex.embeddings.byok")

try:
    from openai import AsyncOpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class BYOKEmbedder:
    """Delegates embedding generation securely preserving tokenomics."""

    __slots__ = ("_default_local", "_api_key", "_model", "_dimension", "_client")

    def __init__(
        self,
        fallback_local: Any,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimension: int = 384,
    ):
        self._default_local = fallback_local
        self._api_key = api_key
        self._model = model
        self._dimension = dimension

        self._client = None
        if self._api_key and HAS_OPENAI:
            self._client = AsyncOpenAI(api_key=self._api_key)

    async def embed(self, text: Union[str, list[str]]) -> Union[list[float], list[list[float]]]:
        if self._client:
            # Delegate to External
            texts = [text] if isinstance(text, str) else text
            try:
                # O(1) external offloading with explicit dimension pruning to keep SQLite happy
                response = await self._client.embeddings.create(
                    input=texts, model=self._model, dimensions=self._dimension
                )
                embeddings = [data.embedding for data in response.data]
                return embeddings[0] if isinstance(text, str) else embeddings
            except (RuntimeError, OSError, ValueError, TypeError) as e:
                logger.error("BYOK Embedding failed: %s. Falling back to default if permitted.", e)  # noqa: G004
                # We can decide to either bounce or fallback

        # Fallback to local (requires strict rate limits upstream)
        logger.warning("Using LocalEmbedder for tenant inference. Subject to CPU tokenomics.")
        return self._default_local.embed(text)
