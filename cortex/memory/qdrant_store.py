# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""
Qdrant-backed VectorStore implementation.
Provides safe, partitioned, CAIR-compatible semantic vector storage.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.memory.vector_store import VectorStore

try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.http import models as rest
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    AsyncQdrantClient = None
    rest = None


logger = logging.getLogger("cortex.memory.qdrant_store")


class QdrantStore(VectorStore):
    """
    Qdrant implementation of VectorStore.
    Each tenant gets isolated within a Qdrant collection, or by payload partitioning.
    For CORTEX CAIR/SCL, we use payload partitioning (tenant_id) within a shared collection
    to avoid massive overhead per tenant, or collection-per-tenant for strict isolation.
    We default to collection-per-tenant for Zero-Trust isolation.
    """

    def __init__(
        self,
        url: str | None = None,
        path: str | None = None,
        api_key: str | None = None,
        embedding_dim: int = 1536,
        prefix: str = "cortex_tenant_",
    ) -> None:
        if not QDRANT_AVAILABLE:
            raise RuntimeError("qdrant-client not installed. Run `pip install qdrant-client`")
        
        # Local file-based or remote
        if path:
            self.client = AsyncQdrantClient(path=path)
        elif url:
            self.client = AsyncQdrantClient(url=url, api_key=api_key)
        else:
            self.client = AsyncQdrantClient(location=":memory:")
            
        self.dim = embedding_dim
        self.prefix = prefix
        self._initialized_collections: set[str] = set()

    async def _ensure_collection(self, tenant_id: str) -> str:
        """Ensure a collection exists for this tenant (Zero-Trust)."""
        collection_name = f"{self.prefix}{tenant_id}"
        if collection_name in self._initialized_collections:
            return collection_name
            
        if not await self.client.collection_exists(collection_name):
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=rest.VectorParams(
                    size=self.dim,
                    distance=rest.Distance.COSINE
                ),
            )
            # Create indexes for typical filters (project, confidence)
            await self.client.create_payload_index(
                collection_name=collection_name,
                field_name="project",
                field_schema=rest.PayloadSchemaType.KEYWORD,
            )
            
        self._initialized_collections.add(collection_name)
        return collection_name

    async def upsert(
        self,
        tenant_id: str,
        fact_id: int,
        vector: list[float],
        payload: dict[str, Any] | None = None,
    ) -> None:
        collection_name = await self._ensure_collection(tenant_id)
        
        point = rest.PointStruct(
            id=fact_id,
            vector=vector,
            payload=payload or {}
        )
        await self.client.upsert(
            collection_name=collection_name,
            points=[point]
        )

    async def query(
        self,
        tenant_id: str,
        vector: list[float],
        k: int,
        filter_opts: dict[str, Any] | None = None,
    ) -> list[tuple[int, float]]:
        collection_name = await self._ensure_collection(tenant_id)
        
        qdrant_filter = None
        if filter_opts:
            must_conditions = []
            if "project" in filter_opts and filter_opts["project"]:
                must_conditions.append(
                    rest.FieldCondition(
                        key="project",
                        match=rest.MatchValue(value=filter_opts["project"])
                    )
                )
            if "confidence" in filter_opts and filter_opts["confidence"]:
                must_conditions.append(
                    rest.FieldCondition(
                        key="confidence",
                        range=rest.Range(gte=float(filter_opts["confidence"]))
                    )
                )
            if must_conditions:
                qdrant_filter = rest.Filter(must=must_conditions)

        results = await self.client.search(
            collection_name=collection_name,
            query_vector=vector,
            query_filter=qdrant_filter,
            limit=k,
            with_payload=False,
            with_vectors=False,
        )
        
        # Qdrant returns score as Cosine Similarity directly.
        # VectorStore contract expects distance (1.0 - similarity).
        return [(int(r.id), 1.0 - r.score) for r in results]

    async def delete(
        self,
        tenant_id: str,
        fact_ids: list[int],
    ) -> None:
        collection_name = await self._ensure_collection(tenant_id)
        await self.client.delete(
            collection_name=collection_name,
            points_selector=rest.PointIdsList(points=fact_ids)
        )
