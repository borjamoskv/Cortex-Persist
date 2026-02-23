"""
CORTEX v5.2 — L2 Vector Store (Qdrant).

Sovereign semantic memory powered by Qdrant's embedded Rust engine.
Zero Docker. Zero network. 100% local. 100% async.

Escalation path: swap ``AsyncQdrantClient(path=...)`` for
``AsyncQdrantClient(url="http://...")`` when traffic demands it.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.models import MemoryEntry

__all__ = ["VectorStoreL2"]

logger = logging.getLogger("cortex.memory.vector_store")

COLLECTION_NAME = "cortex_memories"


class VectorStoreL2:
    """Async vector store for CORTEX L2 semantic memory.

    Uses Qdrant in embedded mode (Rust engine, local disk) by default.
    All operations are fully async — safe for the FastAPI event loop.

    Args:
        db_path: Directory for Qdrant's embedded storage.
        encoder: AsyncEncoder instance for vectorization.
        url: If provided, connect to a remote Qdrant server instead
             of embedded mode. Overrides ``db_path``.
    """

    __slots__ = ("_client", "_encoder", "_ready")

    def __init__(
        self,
        encoder: AsyncEncoder,
        db_path: str | Path = "~/.cortex/vectors",
        url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._encoder = encoder
        resolved = str(Path(db_path).expanduser()) if not url else None

        if url:
            self._client = AsyncQdrantClient(url=url, api_key=api_key)
            logger.info("VectorStoreL2 connected to remote Qdrant: %s", url)
        else:
            self._client = AsyncQdrantClient(path=resolved)
            logger.info("VectorStoreL2 using local storage: %s", resolved)

        self._ready = False

    async def ensure_collection(self) -> None:
        """Create the collection if it doesn't exist (idempotent)."""
        if self._ready:
            return

        collections = await self._client.get_collections()
        exists = any(c.name == COLLECTION_NAME for c in collections.collections)

        if not exists:
            await self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self._encoder.dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "Created collection '%s' (dim=%d, cosine)",
                COLLECTION_NAME,
                self._encoder.dimension,
            )

        self._ready = True

    async def memorize(self, entry: MemoryEntry) -> None:
        """Encode and store a single memory entry."""
        await self.ensure_collection()

        vector = await self._encoder.encode(entry.content)

        await self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=entry.id,
                    vector=vector,
                    payload=entry.to_payload(),
                )
            ],
        )

    async def memorize_batch(self, entries: list[MemoryEntry]) -> int:
        """Encode and store multiple entries. Returns count stored."""
        if not entries:
            return 0

        await self.ensure_collection()

        texts = [e.content for e in entries]
        vectors = await self._encoder.encode_batch(texts)

        points = [
            PointStruct(
                id=entry.id,
                vector=vec,
                payload=entry.to_payload(),
            )
            for entry, vec in zip(entries, vectors, strict=True)
        ]

        await self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )
        return len(points)

    async def recall(
        self,
        query: str,
        limit: int = 5,
        project: str | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories by semantic similarity.

        Args:
            query: Natural language search query.
            limit: Max results to return.
            project: Optional project filter.
            score_threshold: Minimum cosine similarity (0-1).

        Returns:
            List of dicts with ``id``, ``content``, ``score``, and metadata.
        """
        await self.ensure_collection()

        query_vector = await self._encoder.encode(query)

        query_filter = None
        if project:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="project",
                        match=MatchValue(value=project),
                    )
                ]
            )

        results = await self._client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": r.id,
                "content": r.payload.get("content", "") if r.payload else "",
                "score": r.score,
                "project": r.payload.get("project", "") if r.payload else "",
                "source": r.payload.get("source", "") if r.payload else "",
                "created_at": r.payload.get("created_at", "") if r.payload else "",
            }
            for r in results.points
        ]

    async def forget(self, entry_id: str) -> None:
        """Remove a memory by its ID."""
        await self.ensure_collection()
        await self._client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=[entry_id],
        )

    async def count(self) -> int:
        """Return total number of stored memories."""
        await self.ensure_collection()
        info = await self._client.get_collection(COLLECTION_NAME)
        return info.points_count or 0

    async def close(self) -> None:
        """Gracefully close the Qdrant client."""
        await self._client.close()
