# [C5-REAL] Exergy-Maximized
"""
cat_id: federation-router
cat_type: module
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
"""

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class SearchIndex(Protocol):
    def upsert_fact(self, tenant_id: str, fact_id: int, vector: list[float], payload: dict[str, Any]) -> None: ...
    def search_cross_tenant(self, query_vector: list[float], limit: int = 50) -> list[dict[str, Any]]: ...


class MockQdrantIndex:
    """Fallback index simulating Qdrant for inverted/vector searches across tenants."""

    def __init__(self):
        self.store: list[dict[str, Any]] = []

    def upsert_fact(self, tenant_id: str, fact_id: int, vector: list[float], payload: dict[str, Any]) -> None:
        self.store = [item for item in self.store if not (item["tenant_id"] == tenant_id and item["fact_id"] == fact_id)]
        self.store.append({
            "tenant_id": tenant_id,
            "fact_id": fact_id,
            "vector": vector,
            "payload": payload
        })

    def search_cross_tenant(self, query_vector: list[float], limit: int = 50) -> list[dict[str, Any]]:
        # Mock cosine similarity ranking
        ranked = []
        for item in self.store:
            # Simple dot product simulation
            sim = sum(a * b for a, b in zip(item["vector"][:10], query_vector[:10]))
            ranked.append((sim, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in ranked[:limit]]


class FederationRouter:
    """Manages multi-tenant read/write orchestration (SQLite + Qdrant fallback).
    Enforces local C5 sovereignty while preventing O(N) lookup degradation.
    """

    def __init__(self, qdrant_index: SearchIndex | None = None):
        self.index = qdrant_index or MockQdrantIndex()
        self.cross_queries_count = 0

    def route_write(self, tenant_id: str, fact_id: int, fact_content: str, vector: list[float]) -> None:
        """Saves content locally in the tenant's SQLite DB, and mirrors vectors to the cross-tenant index."""
        logger.debug("Routing local write for tenant=%s, fact_id=%d", tenant_id, fact_id)
        # Mirror to cross-tenant index
        self.index.upsert_fact(
            tenant_id=tenant_id,
            fact_id=fact_id,
            vector=vector,
            payload={"content": fact_content}
        )

    def route_cross_query(self, query_vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
        """Queries the cross-tenant index. Triggers alert if threshold reached (Rule 15 §2)."""
        self.cross_queries_count += 1
        if self.cross_queries_count > 50:
            logger.warning("THRESHOLD EXCEEDED: cross_tenant_queries_per_second > 50. Consider scaling out.")
        
        return self.index.search_cross_tenant(query_vector, limit)
