from __future__ import annotations

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from .base import VectorStoreProvider

logger = logging.getLogger("cortex.memory.vector_providers.qdrant")


class QdrantProvider(VectorStoreProvider):
    """Qdrant-based implementation of L2 Vector Store."""

    def __init__(self, path: str | None = None, url: str | None = None) -> None:
        if url:
            self._client = AsyncQdrantClient(url=url)
        else:
            self._client = AsyncQdrantClient(path=path)
        self._ready_collections: set[str] = set()

    async def ensure_collection(self, collection_name: str, dimension: int) -> None:
        if collection_name in self._ready_collections:
            return

        collections = await self._client.get_collections()
        exists = any(c.name == collection_name for c in collections.collections)

        if not exists:
            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "Created Qdrant collection '%s' (dim=%d)",
                collection_name,
                dimension,
            )

        self._ready_collections.add(collection_name)

    async def upsert(
        self,
        collection_name: str,
        entries: list[tuple[str, list[float], dict[str, Any]]],
    ) -> None:
        points = [
            PointStruct(id=entry_id, vector=vector, payload=payload)
            for entry_id, vector, payload in entries
        ]
        await self._client.upsert(
            collection_name=collection_name,
            points=points,
        )

    async def query(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        query_filter: Any | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        results = await self._client.query_points(
            collection_name=collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
        )
        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload or {},
            }
            for r in results.points
        ]

    async def delete(self, collection_name: str, ids: list[str]) -> None:
        await self._client.delete(
            collection_name=collection_name,
            points_selector=ids,
        )

    async def get_count(self, collection_name: str) -> int:
        info = await self._client.get_collection(collection_name)
        return info.points_count or 0

    async def close(self) -> None:
        await self._client.close()
