# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
from typing import Any

from babylon60.embeddings.registry import get_provider

__all__ = ["EmbeddingManager"]

logger = logging.getLogger("babylon60.embeddings.manager")


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
        from babylon60.core import config

        return config.EMBEDDINGS_MODE

    @property
    def provider(self) -> str:
        """Return the configured provider name."""
        from babylon60.core import config

        return config.EMBEDDINGS_PROVIDER

    @property
    def is_cloud(self) -> bool:
        """Return True if using a cloud/API provider."""
        return self.mode == "api"

    def _get_embedder(self) -> Any:
        """Lazy-load the appropriate embedder based on config via the registry."""
        if self._embedder is not None:
            return self._embedder

        provider_type = "api" if self.mode == "api" else "local"

        try:
            self._embedder = get_provider(provider_type)
            logger.info(
                "Embedder initialized: %s (mode=%s)",
                provider_type,
                self.mode,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to initialize embedder: {exc}") from exc

        return self._embedder

    def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Generate embedding for a single text or batch."""
        if self.mode == "api":
            raise RuntimeError("Synchronous embed() is unavailable in API mode; use aembed().")
        return self._get_embedder().embed(text)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if self.mode == "api":
            raise RuntimeError(
                "Synchronous embed_batch() is unavailable in API mode; use aembed_batch()."
            )
        return self._get_embedder().embed_batch(texts, batch_size=batch_size)

    async def aembed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Async embedding API that supports both local and cloud backends."""
        embedder = self._get_embedder()
        if self.mode == "api":
            return await embedder.embed(text)  # type: ignore[reportGeneralTypeIssues]
        import asyncio

        return await asyncio.to_thread(embedder.embed, text)

    async def aembed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Async batch embedding API that supports both local and cloud backends."""
        embedder = self._get_embedder()
        if self.mode == "api":
            return await embedder.embed_batch(texts, batch_size=batch_size)  # type: ignore[reportGeneralTypeIssues]
        import asyncio

        return await asyncio.to_thread(embedder.embed_batch, texts, batch_size=batch_size)

    async def embed_multimodal(
        self,
        parts: list[dict[str, Any]],
        task_type: str | None = None,
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

        return await embedder.embed_multimodal(parts, task_type=task_type)  # type: ignore[type-error]

    async def embed_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        task_type: str | None = None,
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

        return await embedder.embed_image(image_bytes, mime_type=mime_type, task_type=task_type)  # type: ignore[type-error]

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
        from babylon60.engine.core.embedding_engine import embed_fact_async
        from babylon60.engine.meta.metadata_engine import MetadataEngine

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

    async def check_and_reindex(self, tenant_id: str = "default") -> None:
        """Sovereign Boot Sequence: Check dimension alignment and re-index if mutated."""
        from babylon60.embeddings.reindex import ReindexPipeline

        pipeline = ReindexPipeline(self.engine, self)
        current_dim = await pipeline.get_current_db_dimension()

        target_dim = self.dimension

        if current_dim is not None and current_dim != target_dim:
            logger.warning(
                "Embedding dimension mismatch detected (DB: %d, Provider: %d). "
                "Initiating Re-indexing Pipeline (Ω₁)...",
                current_dim,
                target_dim,
            )
            results = await pipeline.execute_reindex(tenant_id=tenant_id)
            logger.info("Re-indexing complete: %s", results)
        else:
            logger.debug("Embedding dimensions aligned (%d). No re-index needed.", target_dim)
