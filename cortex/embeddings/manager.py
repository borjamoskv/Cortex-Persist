"""Embedding Sovereign Layer — EmbeddingManager for CORTEX."""

from __future__ import annotations

import logging
from typing import Any, Optional

from cortex.embeddings import LocalEmbedder

__all__ = ["EmbeddingManager"]

logger = logging.getLogger("cortex.embeddings.manager")


class EmbeddingManager:
    """Manages the generation and lifecycle of embeddings.

    When CORTEX_EMBEDDINGS=api, uses APIEmbedder (cloud providers).
    When CORTEX_EMBEDDINGS=local (default), uses LocalEmbedder (ONNX).
    """

    def __init__(self, engine):
        self.engine = engine
        self._embedder = None

    @property
    def mode(self) -> str:
        """Return the current embeddings mode (local|api)."""
        from cortex import config

        return config.EMBEDDINGS_MODE

    @property
    def provider(self) -> str:
        """Return the configured provider name."""
        from cortex import config

        return config.EMBEDDINGS_PROVIDER

    @property
    def is_cloud(self) -> bool:
        """Return True if using a cloud/API provider."""
        return self.mode == "api"

    def _get_embedder(self) -> LocalEmbedder | Any:
        """Lazy-load the appropriate embedder based on config."""
        if self._embedder is not None:
            return self._embedder

        if self.mode == "api":
            from cortex import config
            from cortex.embeddings.api_embedder import APIEmbedder

            self._embedder = APIEmbedder(
                provider=config.EMBEDDINGS_PROVIDER,
                target_dimension=config.EMBEDDINGS_DIMENSION,
                task_type=config.EMBEDDINGS_TASK_TYPE,
            )
            logger.info(
                "API embedder initialized: %s (dim=%d)",
                config.EMBEDDINGS_PROVIDER,
                config.EMBEDDINGS_DIMENSION,
            )
        else:
            self._embedder = LocalEmbedder()
            logger.info("Local embedder initialized (dim=384)")

        return self._embedder

    def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Generate embedding for a single text or batch."""
        return self._get_embedder().embed(text)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return self._get_embedder().embed_batch(texts, batch_size=batch_size)

    async def embed_multimodal(
        self,
        parts: list[dict[str, Any]],
        task_type: Optional[str] = None,
    ) -> list[float]:
        """Generate multimodal embedding (gemini-v2 only).

        Args:
            parts: Gemini content parts (text, inline_data, file_data).
            task_type: Override default task_type.

        Returns:
            Embedding vector.

        Raises:
            ValueError: If provider doesn't support multimodal.
            RuntimeError: If not in API mode.
        """
        if self.mode != "api":
            raise RuntimeError(
                "Multimodal embeddings require API mode. "
                "Set CORTEX_EMBEDDINGS=api and CORTEX_EMBEDDINGS_PROVIDER=gemini-v2"
            )

        embedder = self._get_embedder()
        if not hasattr(embedder, "embed_multimodal"):
            raise RuntimeError("Current embedder does not support multimodal")

        return await embedder.embed_multimodal(parts, task_type=task_type)  # type: ignore

    async def embed_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        task_type: Optional[str] = None,
    ) -> list[float]:
        """Embed a single image (gemini-v2 only)."""
        if self.mode != "api":
            raise RuntimeError(
                "Image embeddings require API mode. "
                "Set CORTEX_EMBEDDINGS=api and CORTEX_EMBEDDINGS_PROVIDER=gemini-v2"
            )

        embedder = self._get_embedder()
        if not hasattr(embedder, "embed_image"):
            raise RuntimeError("Current embedder does not support image embedding")

        return await embedder.embed_image(image_bytes, mime_type=mime_type, task_type=task_type)  # type: ignore

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._get_embedder().dimension

    @property
    def supports_multimodal(self) -> bool:
        """Return True if current embedder supports multimodal input."""
        embedder = self._get_embedder()
        return getattr(embedder, "supports_multimodal", False)

    async def enrich_fact(
        self,
        fact_id: int,
        content: str,
        project: str,
        tenant_id: str = "default",
    ) -> None:
        """Sovereign Enrichment (Ω₁₃): Vector embedding + Metadata Refinement.

        This method is called by the EnrichmentWorker to finalize a fact's
        entry into the Double-Plane architecture.
        """
        from cortex.engine.embedding_engine import embed_fact_async
        from cortex.engine.metadata_engine import MetadataEngine

        async with self.engine.session() as conn:
            # 1. Dense & Specular Embeddings
            await embed_fact_async(
                conn,
                fact_id,
                project,
                content,
                self._get_embedder(),
                self.engine._memory_manager,
                tenant_id,
            )

            # 2. Async Semantic Enrichment (V2 Refinement)
            metadata = await MetadataEngine.enrich_async(fact_id, content, self.engine)

            # 3. Update Multi-Plane Metadata
            query = """
                UPDATE facts_meta
                SET category = COALESCE(?, category),
                    yield_score = COALESCE(?, yield_score),
                    exergy_score = COALESCE(?, exergy_score)
                WHERE fact_id = ?
            """
            await conn.execute(
                query,
                (
                    metadata.get("category"),
                    metadata.get("yield_score"),
                    metadata.get("exergy_score"),
                    fact_id,
                ),
            )
            await conn.commit()
            logger.info("Fact #%d enriched: vector + metadata refined (V2)", fact_id)
