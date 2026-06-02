# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""
VectorStore Protocol - Abstract boundary for semantic retrieval.
CAIR/SCL compatible. Ensures that core engine is backend-agnostic.
"""

from __future__ import annotations
from typing import Any, Protocol

__all__ = ["VectorStore"]


class VectorStore(Protocol):
    """
    Core Abstraction for Vector Search (CAIR/SCL compatible).
    Enforces isolation by tenant_id at the interface level.
    """

    async def upsert(
        self,
        tenant_id: str,
        fact_id: int,
        vector: list[float],
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Insert or update a semantic vector.
        
        Args:
            tenant_id: The isolation boundary identifier.
            fact_id: The unique ID of the fact in the ledger.
            vector: The dense embedding vector.
            payload: Optional metadata for pre-filtering (e.g. project, confidence).
        """
        ...

    async def query(
        self,
        tenant_id: str,
        vector: list[float],
        k: int,
        filter_opts: dict[str, Any] | None = None,
    ) -> list[tuple[int, float]]:
        """
        Query for the K nearest vectors within the tenant partition.
        
        Args:
            tenant_id: The isolation boundary identifier.
            vector: The dense query vector.
            k: The maximum number of results to return.
            filter_opts: Optional dictionary of metadata filters.
            
        Returns:
            A list of tuples (fact_id, distance).
            Distance is typically 1.0 - cosine_similarity (lower is better).
        """
        ...

    async def delete(
        self,
        tenant_id: str,
        fact_ids: list[int],
    ) -> None:
        """
        Delete vectors by fact_id.
        """
        ...
