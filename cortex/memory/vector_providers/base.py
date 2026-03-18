from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VectorStoreProvider(ABC):
    """Base abstract class for L2 Vector Store providers."""

    @abstractmethod
    async def ensure_collection(self, collection_name: str, dimension: int) -> None:
        """Ensure the collection exists."""
        pass

    @abstractmethod
    async def upsert(
        self,
        collection_name: str,
        entries: list[tuple[str, list[float], dict[str, Any]]],
    ) -> None:
        """Upsert points into the collection."""
        pass

    @abstractmethod
    async def query(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        query_filter: Any | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Query for similar vectors."""
        pass

    @abstractmethod
    async def delete(self, collection_name: str, ids: list[str]) -> None:
        """Delete points by ID."""
        pass

    @abstractmethod
    async def get_count(self, collection_name: str) -> int:
        """Get total point count."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Release resources."""
        pass
