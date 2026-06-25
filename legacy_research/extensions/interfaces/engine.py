# [C5-REAL] Exergy-Maximized
"""Engine Protocol - Minimal contract for downstream module consumption.

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

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------


@runtime_checkable
class EngineProtocol(Protocol):
    """Minimal engine contract for downstream consumers.

    Provides connection access, session management, and core operations
    without coupling to the full CortexEngine implementation.
    """

    _db_path: Path
    _vec_available: bool

    @property
    def memory(self) -> Any: ...

    @property
    def embeddings(self) -> Any: ...

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
        tags: list[str] | None = None,
        confidence: str = "stated",
        source: str | None = None,
        meta: dict[str, Any] | None = None,
        valid_from: str | None = None,
        commit: bool = True,
        tx_id: int | None = None,
        conn: aiosqlite.Connection | None = None,
        **kwargs: Any,
    ) -> int:
        """Store a fact and return its ID."""
        ...

    async def store_many(self, facts: list[dict[str, Any]]) -> list[int]:
        """Store multiple facts in a transaction."""
        ...

    async def get_fact(self, fact_id: int) -> Any | None:
        """Get fact by ID."""
        ...

    async def get_all_active_facts(
        self,
        tenant_id: str = "default",
        project: str | None = None,
        fact_types: list[str] | None = None,
    ) -> list[Any]:
        """Get all active facts matching criteria."""
        ...

    async def recall(
        self,
        project: str,
        query: str | None = None,
        tenant_id: str = "default",
        **kwargs: Any,
    ) -> list[Any]:
        """Recall facts matching criteria."""
        ...

    async def history(
        self,
        project: str,
        tenant_id: str = "default",
        as_of: str | None = None,
    ) -> list[Any]:
        """Temporal history."""
        ...

    async def time_travel(
        self,
        tenant_id: str = "default",
        tx_id: int | None = None,
    ) -> list[Any]:
        """Project state reconstruction."""
        ...

    async def search(
        self,
        query: str,
        tenant_id: str = "default",
        top_k: int = 5,
        project: str | None = None,
        as_of: str | None = None,
        graph_depth: int = 0,
        include_graph: bool = False,
        confidence: str | None = None,
        causal_gap: Any | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """Semantic/hybrid search."""
        ...

    async def deprecate(
        self,
        fact_id: int,
        reason: str | None = None,
        conn: aiosqlite.Connection | None = None,
        tenant_id: str = "default",
    ) -> bool:
        """Soft-delete a fact."""
        ...

    async def register_ghost(
        self,
        reference: str,
        context: str,
        project: str,
        target_file: str | Path | None = None,
        conn: aiosqlite.Connection | None = None,
        root_dir: Path | None = None,
    ) -> str:
        """Register a ghost fact."""
        ...

    async def stats(self) -> dict[str, Any]:
        """System stats."""
        ...

    async def health_check(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Engine health status."""
        ...

    async def health_report(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Detailed security/health report."""
        ...

    async def close(self) -> None:
        """Release resources."""
        ...
