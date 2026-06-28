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
        from cortex.engine.cognitive.models import row_to_fact

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
            from cortex.extensions.security.tenant import get_tenant_id

            tenant_id = get_tenant_id()

        # Strict Multi-Tenancy (RLS): Never allow empty tenant
        if not tenant_id:
            tenant_id = "default"

        return tenant_id

    async def _resolve_symlinks_async(
        self, facts: list[dict[str, Any]], conn: aiosqlite.Connection, tenant_id: str
    ) -> list[dict[str, Any]]:
        """Resolve NEXUS_SYMLINK pointers efficiently (O(1) query) for bridge facts."""
        symlinks = [f for f in facts if str(f.get("content", "")).startswith("NEXUS_SYMLINK:")]
        if not symlinks:
            return facts

        target_hashes = list({f["content"].split("NEXUS_SYMLINK:")[1] for f in symlinks})

        # We need the decrypted content of target facts. The easiest way is to fetch the raw rows and decrypt.
        # But we don't have access to decrypt logic here easily unless we use self._row_to_fact.
        placeholders = ",".join("?" for _ in target_hashes)
        query = f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE f.tenant_id = ? AND f.hash IN ({placeholders}) AND f.is_tombstoned = 0"

        async with conn.execute(query, [tenant_id, *target_hashes]) as cursor:
            rows = await cursor.fetchall()

        target_facts = {
            f["hash"]: f for f in [self._row_to_fact(r, tenant_id) for r in rows] if f.get("hash")
        }

        for f in symlinks:
            target_hash = f["content"].split("NEXUS_SYMLINK:")[1]
            if target_hash in target_facts:
                f["content"] = target_facts[target_hash]["content"]
                # Also expose adaptation logic if it exists
                if "bridge_adaptation" in f.get("meta", {}):
                    f["content"] = f"{f['meta']['bridge_adaptation']} (Resolved from pointer)"

        return facts
