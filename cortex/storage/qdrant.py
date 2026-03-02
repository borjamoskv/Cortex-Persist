"""
CORTEX v6.0 — Qdrant Vector Store Backend.

Production-grade vector search backend using Qdrant.
Drop-in replacement for sqlite-vec (fact_embeddings virtual table).

Usage:
    CORTEX_VECTOR_BACKEND=qdrant
    QDRANT_URL=http://localhost:6333

Collection naming: one Qdrant collection per tenant.
    tenant_id="default" → collection "cortex_default"
    tenant_id="acme"    → collection "cortex_acme"

This ensures true vector-level isolation between tenants.
"""

from __future__ import annotations

import logging
from typing import Any, Final, Protocol, runtime_checkable

__all__ = ["VectorBackend", "QdrantVectorBackend", "get_vector_backend"]

logger = logging.getLogger("cortex.storage.qdrant")

# Vector dimension (all-MiniLM-L6-v2)
VECTOR_DIM: Final[int] = 384

# Collection prefix to avoid namespace collisions
COLLECTION_PREFIX: Final[str] = "cortex_"


# ─── Protocol ───────────────────────────────────────────────────────


@runtime_checkable
class VectorBackend(Protocol):
    """Protocol for vector store backends.

    Implementations must support:
    - upsert: Store fact_id + embedding
    - search: KNN search returning [(fact_id, score)]
    - delete: Remove embedding for a fact
    - health_check: Verify connectivity
    """

    async def upsert(
        self,
        fact_id: int,
        embedding: list[float],
        tenant_id: str = "default",
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Upsert a vector embedding for a fact."""
        ...

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> list[tuple[int, float]]:
        """KNN search. Returns [(fact_id, score)] sorted by score DESC."""
        ...

    async def delete(self, fact_id: int, tenant_id: str = "default") -> None:
        """Delete the vector for a given fact."""
        ...

    async def health_check(self) -> bool:
        """Return True if the vector store is reachable."""
        ...

    async def close(self) -> None:
        """Close any connections."""
        ...


# ─── Qdrant Implementation ───────────────────────────────────────────


class QdrantVectorBackend:
    """Production vector search backend using Qdrant.

    Features:
    - Per-tenant Qdrant collections (true data isolation)
    - Cosine similarity (same metric as all-MiniLM-L6-v2 normalization)
    - Payload filtering by project
    - Auto-creates collections on first upsert
    - Idempotent upsert (overwrites on same fact_id)
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: str | None = None,
        *,
        dim: int = VECTOR_DIM,
    ):
        self.url = url
        self._api_key = api_key
        self._dim = dim
        self._client: Any = None
        self._initialized_collections: set[str] = set()

    def _collection_name(self, tenant_id: str) -> str:
        """Generate per-tenant collection name."""
        # Sanitize tenant_id: alphanumeric + underscore only
        safe = "".join(c if c.isalnum() or c == "_" else "_" for c in tenant_id)
        return f"{COLLECTION_PREFIX}{safe}"

    async def connect(self) -> None:
        """Initialize the Qdrant client."""
        if self._client is not None:
            return

        try:
            from qdrant_client import AsyncQdrantClient
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client required for Qdrant backend. Run: pip install qdrant-client"
            ) from exc

        logger.info("Connecting to Qdrant at %s", self.url)
        self._client = AsyncQdrantClient(
            url=self.url,
            api_key=self._api_key,
        )
        logger.info("Qdrant: Client initialized.")

    def _ensure_client(self) -> None:
        if self._client is None:
            raise RuntimeError("QdrantVectorBackend not connected. Call connect() first.")

    async def _ensure_collection(self, collection: str) -> None:
        """Create collection if it doesn't exist (idempotent)."""
        if collection in self._initialized_collections:
            return

        from qdrant_client.models import Distance, VectorParams

        try:
            exists = await self._client.collection_exists(collection)
            if not exists:
                await self._client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=self._dim,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Qdrant: Created collection '%s' (dim=%d)", collection, self._dim)
            else:
                logger.debug("Qdrant: Collection '%s' already exists.", collection)
        except (RuntimeError, OSError, ValueError) as exc:
            logger.error("Qdrant: Failed to ensure collection '%s': %s", collection, exc)
            raise

        self._initialized_collections.add(collection)

    async def upsert(
        self,
        fact_id: int,
        embedding: list[float],
        tenant_id: str = "default",
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Upsert a vector embedding.

        Args:
            fact_id: The fact's primary key (used as Qdrant point ID).
            embedding: 384-dimensional float vector.
            tenant_id: Routes to the correct collection.
            payload: Optional metadata stored alongside the vector
                     (e.g., project, fact_type for server-side filtering).
        """
        self._ensure_client()
        collection = self._collection_name(tenant_id)
        await self._ensure_collection(collection)

        from qdrant_client.models import PointStruct

        point = PointStruct(
            id=fact_id,
            vector=embedding,
            payload=payload or {},
        )

        try:
            await self._client.upsert(
                collection_name=collection,
                points=[point],
            )
            logger.debug("Qdrant: Upserted fact_id=%d in '%s'", fact_id, collection)
        except (RuntimeError, OSError, ValueError) as exc:
            logger.error("Qdrant: Upsert failed for fact_id=%d: %s", fact_id, exc)
            raise

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> list[tuple[int, float]]:
        """KNN vector search with optional project filter.

        Args:
            query_embedding: Query vector (384-dim).
            top_k: Number of results to return.
            tenant_id: Routes to the correct collection.
            project: If set, filters results to this project only.

        Returns:
            List of (fact_id, score) tuples sorted by score DESC.
            Score is cosine similarity in [0, 1].
        """
        self._ensure_client()
        collection = self._collection_name(tenant_id)

        # Skip search if collection not yet initialized
        if collection not in self._initialized_collections:
            try:
                exists = await self._client.collection_exists(collection)
                if not exists:
                    return []
                self._initialized_collections.add(collection)
            except (RuntimeError, OSError, ValueError):
                return []

        query_filter = None
        if project:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            query_filter = Filter(
                must=[FieldCondition(key="project", match=MatchValue(value=project))]
            )

        try:
            results = await self._client.search(
                collection_name=collection,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=query_filter,
                with_payload=False,
            )
            return [(int(hit.id), float(hit.score)) for hit in results]
        except (RuntimeError, OSError, ValueError) as exc:
            logger.error("Qdrant: Search failed in '%s': %s", collection, exc)
            return []

    async def delete(self, fact_id: int, tenant_id: str = "default") -> None:
        """Delete a vector point by fact_id."""
        self._ensure_client()
        collection = self._collection_name(tenant_id)

        from qdrant_client.models import PointIdsList

        try:
            await self._client.delete(
                collection_name=collection,
                points_selector=PointIdsList(points=[fact_id]),
            )
            logger.debug("Qdrant: Deleted fact_id=%d from '%s'", fact_id, collection)
        except (RuntimeError, OSError, ValueError) as exc:
            logger.error("Qdrant: Delete failed for fact_id=%d: %s", fact_id, exc)
            raise

    async def health_check(self) -> bool:
        """Verify Qdrant is reachable."""
        if self._client is None:
            return False
        try:
            await self._client.get_collections()
            return True
        except (RuntimeError, OSError, ConnectionError):
            return False

    async def close(self) -> None:
        """Close the Qdrant client."""
        if self._client:
            try:
                await self._client.close()
                logger.debug("Qdrant: Client closed.")
            except (RuntimeError, OSError) as exc:
                logger.warning("Qdrant: Unclean close: %s", exc)
            finally:
                self._client = None
                self._initialized_collections.clear()

    def __repr__(self) -> str:
        connected = self._client is not None
        return f"<QdrantVectorBackend url={self.url!r} connected={connected}>"


# ─── Factory ─────────────────────────────────────────────────────────

_vector_backend: VectorBackend | None = None


def get_vector_backend() -> VectorBackend | None:
    """Get the active vector backend singleton (None if using local sqlite-vec)."""
    return _vector_backend


async def init_vector_backend(
    url: str | None = None,
    api_key: str | None = None,
) -> VectorBackend | None:
    """Initialize the global vector backend from environment or parameters.

    Returns None if CORTEX_VECTOR_BACKEND is not set (uses sqlite-vec).

    Usage:
        CORTEX_VECTOR_BACKEND=qdrant
        QDRANT_URL=http://localhost:6333
        QDRANT_API_KEY=...  (optional, for Qdrant Cloud)
    """
    import os

    global _vector_backend

    backend_mode = os.environ.get("CORTEX_VECTOR_BACKEND", "sqlite").lower()
    if backend_mode != "qdrant":
        logger.debug(
            "Vector backend: sqlite-vec (local). Set CORTEX_VECTOR_BACKEND=qdrant to enable Qdrant."
        )
        return None

    qdrant_url = url or os.environ.get("QDRANT_URL", "http://localhost:6333")
    qdrant_key = api_key or os.environ.get("QDRANT_API_KEY")

    backend = QdrantVectorBackend(url=qdrant_url, api_key=qdrant_key)
    await backend.connect()

    _vector_backend = backend
    logger.info("Vector backend: Qdrant at %s", qdrant_url)
    return backend
