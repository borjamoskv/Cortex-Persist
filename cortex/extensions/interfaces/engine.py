"""Engine Protocol — Minimal contract for downstream module consumption.

Modules like guards, shannon, fingerprint, and policy should depend on
this Protocol rather than importing cortex.engine.CortexEngine directly.
This breaks circular dependencies at the package boundary.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

import aiosqlite


@runtime_checkable
class EngineProtocol(Protocol):
    """Minimal engine contract for downstream consumers.

    Provides connection access, session management, and core operations
    without coupling to the full CortexEngine implementation.
    """
    _db_path: Path
    _vec_available: bool

    @property
    def memory(self) -> Any:
        ...

    @property
    def embeddings(self) -> Any:
        ...

    def _resolve_tenant(self, tenant_id: str) -> str:
        """Resolve tenant namespace."""
        ...

    async def get_conn(self) -> aiosqlite.Connection:
        """Returns the async database connection."""
        ...

    @asynccontextmanager
    async def session(self) -> AsyncIterator[aiosqlite.Connection]:
        """Provide a transactional session."""
        ...  # pragma: no cover
        yield  # type: ignore[misc]

    async def store(
        self,
        project: str,
        content: str,
        tenant_id: str = "default",
        fact_type: str = "knowledge",
        tags: Optional[list[str]] = None,
        confidence: str = "stated",
        source: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> int:
        """Store a fact and return its ID."""
        ...

    async def store_many(self, facts: list[dict[str, Any]]) -> list[int]:
        """Store multiple facts in a transaction."""
        ...

    async def get_fact(self, fact_id: int) -> Optional[Any]:
        """Get fact by ID."""
        ...

    async def get_all_active_facts(
        self,
        tenant_id: str = "default",
        project: Optional[str] = None,
        fact_types: Optional[list[str]] = None,
    ) -> list[Any]:
        """Get all active facts matching criteria."""
        ...

    async def recall(
        self,
        project: str,
        query: Optional[str] = None,
        tenant_id: str = "default",
        **kwargs: Any,
    ) -> list[Any]:
        """Recall facts matching criteria."""
        ...

    async def history(
        self,
        project: str,
        tenant_id: str = "default",
        as_of: Optional[str] = None,
    ) -> list[Any]:
        """Temporal history."""
        ...

    async def time_travel(
        self,
        tenant_id: str = "default",
        tx_id: Optional[int] = None,
    ) -> list[Any]:
        """Project state reconstruction."""
        ...

    async def search(
        self,
        query: str,
        project: Optional[str] = None,
        tenant_id: str = "default",
        **kwargs: Any,
    ) -> list[Any]:
        """Semantic/hybrid search."""
        ...

    async def deprecate(
        self,
        fact_id: int,
        reason: Optional[str] = None,
        conn: Optional[aiosqlite.Connection] = None,
        tenant_id: str = "default",
    ) -> bool:
        """Soft-delete a fact."""
        ...

    async def register_ghost(
        self,
        reference: str,
        context: str,
        project: str,
        target_file: Optional[str | Path] = None,
        conn: Optional[aiosqlite.Connection] = None,
        root_dir: Optional[Path] = None,
    ) -> str:
        """Register a ghost fact."""
        ...

    async def stats(self) -> dict[str, Any]:
        """System stats."""
        ...

    async def close(self) -> None:
        """Release resources."""
        ...
