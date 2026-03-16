"""Engine Protocol — Minimal contract for downstream module consumption.

Modules like guards, shannon, fingerprint, and policy should depend on
this Protocol rather than importing cortex.engine.CortexEngine directly.
This breaks circular dependencies at the package boundary.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import aiosqlite


@runtime_checkable
class EngineProtocol(Protocol):
    """Minimal engine contract for downstream consumers.

    Provides connection access, session management, and core operations
    without coupling to the full CortexEngine implementation.
    """

    _db_path: Path
    _vec_available: bool

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
        tags: list[str] | None = None,
        confidence: str = "stated",
        source: str | None = None,
        meta: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> int:
        """Store a fact and return its ID."""
        ...

    async def recall(
        self,
        project: str,
        query: str | None = None,
        tenant_id: str = "default",
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Recall facts matching criteria."""
        ...

    async def search(
        self,
        query: str,
        project: str | None = None,
        tenant_id: str = "default",
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Semantic/hybrid search."""
        ...

    async def deprecate(
        self,
        fact_id: int,
        reason: str | None = None,
        tenant_id: str = "default",
        **kwargs: Any,
    ) -> bool:
        """Soft-delete a fact."""
        ...

    async def close(self) -> None:
        """Release resources."""
        ...
