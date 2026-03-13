"""Engine Mixin Base — The sovereign foundation for all engine sub-layers.
Ω₂: Thermodynamic optimization via shared abstractions.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite

__all__ = ["EngineMixinBase"]

logger = logging.getLogger("cortex.engine")

# Canonical Fact query structure
FACT_COLUMNS = (
    "f.id, f.tenant_id, f.project, f.content, f.fact_type, f.tags, f.meta, "
    "f.hash, f.created_at, f.updated_at, f.is_tombstoned"
)
FACT_JOIN = "FROM facts f"


class EngineMixinBase:
    """Base class for all Engine Mixins to share core database and security logic."""

    @asynccontextmanager
    async def session(self) -> AsyncIterator[aiosqlite.Connection]:
        """Provide a transactional session from the connection pool."""
        # This will be implemented by AsyncCortexEngine
        if False:
            yield  # type: ignore
        raise NotImplementedError("Mixins must be used with a class that implements session()")

    def _get_embedder(self) -> Any:
        """Provide the embedding model."""
        raise NotImplementedError

    def _get_sync_conn(self) -> Any:
        """Provide a synchronous database connection."""
        raise NotImplementedError

    def get_conn(self) -> Any:
        """Provide an asynchronous database connection."""
        raise NotImplementedError

    async def _log_transaction(
        self, conn: aiosqlite.Connection, project: str, action: str, details: dict[str, Any]
    ) -> int:
        """Log a transaction to the ledger."""
        raise NotImplementedError

    async def search(self, *args, **kwargs) -> Any:
        """Perform hybrid search."""
        raise NotImplementedError

    def _row_to_fact(self, row: dict | aiosqlite.Row, tenant_id: str) -> dict[str, Any]:
        """Convert a database row to a decrypted fact dictionary.

        aiosqlite returns tuple-like rows (not sqlite3.Row with named keys),
        so we delegate to row_to_fact() which handles positional indexing correctly.
        """
        from cortex.engine.models import row_to_fact

        fact = row_to_fact(row)  # type: ignore[reportArgumentType]
        return {
            "id": fact.id,
            "tenant_id": fact.tenant_id,
            "project": fact.project,
            "content": fact.content,
            "fact_type": fact.fact_type,
            "type": fact.fact_type,  # API compat alias
            "tags": fact.tags,
            "confidence": fact.meta.get("confidence", "C5") if fact.meta else "C5",
            "valid_from": fact.meta.get("valid_from") if fact.meta else fact.created_at,
            "valid_until": "9999-12-31T23:59:59Z" if fact.is_tombstoned else None,
            "source": fact.meta.get("source", "system") if fact.meta else "system",
            "meta": fact.meta,
            "consensus_score": fact.meta.get("consensus_score", 1.0) if fact.meta else 1.0,
            "created_at": fact.created_at,
            "updated_at": fact.updated_at,
            "tx_id": fact.meta.get("tx_id") if fact.meta else None,
            "parent_decision_id": fact.meta.get("parent_decision_id") if fact.meta else None,
            "hash": fact.hash,
        }

    def _resolve_tenant(self, tenant_id: str) -> str:
        """Resolve and validate the tenant ID from context if 'default' is provided."""
        if tenant_id == "default":
            from cortex.security.tenant import get_tenant_id

            tenant_id = get_tenant_id()

        # Strict Multi-Tenancy (RLS): Never allow empty tenant
        if not tenant_id:
            tenant_id = "default"

        return tenant_id
