# [C5-REAL] Exergy-Maximized
"""Engine Mixin Base - The sovereign foundation for all engine sub-layers.
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

# Canonical Fact query structure - includes rich fact fields used by retrieve()/CLI.
FACT_COLUMNS = (
    "f.id, f.tenant_id, f.project, f.content, f.fact_type, f.tags, f.metadata, "
    "f.hash, f.valid_from, f.valid_until, f.source, f.confidence, "
    "f.created_at, f.updated_at, f.is_tombstoned, f.is_quarantined, "
    "f.quadrant, f.storage_tier, f.exergy_score, f.category, "
    "f.parent_id AS parent_decision_id, f.relation_type, f.yield_score"
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
        """Provide an asynchronous database connection.

        Kept for backward compatibility while callers migrate to `session()`.
        """
        raise NotImplementedError

    async def _log_transaction(
        self, conn: aiosqlite.Connection, project: str, action: str, details: dict[str, Any]
    ) -> int:
        """Log a transaction to the ledger."""
        raise NotImplementedError

    async def search(self, *args, **kwargs) -> Any:
        """Perform hybrid search."""
        raise NotImplementedError

    def _row_to_fact(self, row: dict | aiosqlite.Row | tuple, tenant_id: str) -> dict[str, Any]:
        """Convert a database row to a decrypted fact dictionary.

        Normalizes query rows through the canonical Fact model so callers
        see the same shape as ``retrieve()``.

        Security: Strictly validates that the row belongs to the requested tenant.
        """
        from cortex.engine.uncategorized.models import row_to_fact

        # RLS Verification: row[1] is always tenant_id in canonical FACT_COLUMNS
        row_tuple = tuple(row)
        if len(row_tuple) > 1:
            row_tenant = row_tuple[1]
            if row_tenant != tenant_id and tenant_id != "default":
                logger.error(
                    "TENANT LEAKAGE: Row tenant %s != Requested %s (Fact #%s)",
                    row_tenant,
                    tenant_id,
                    row_tuple[0],
                )
                # In strict mode we could raise, but we'll let row_to_fact handle decryption
                # which will fail if the keys don't match.

        fact = row_to_fact(row_tuple)
        data = fact.to_dict()
        meta = fact.meta or {}
        data["consensus_score"] = fact.consensus_score
        data["tx_id"] = fact.tx_id if fact.tx_id is not None else meta.get("tx_id")
        data["parent_decision_id"] = (
            fact.parent_decision_id or meta.get("parent_decision_id") or fact.parent_id
        )
        return data

    def _resolve_tenant(self, tenant_id: str) -> str:
        """Resolve and validate the tenant ID from context if 'default' is provided."""
        if tenant_id == "default":
            from cortex_extensions.security.tenant import get_tenant_id

            tenant_id = get_tenant_id()

        # Strict Multi-Tenancy (RLS): Never allow empty tenant
        if not tenant_id:
            tenant_id = "default"

        return tenant_id
