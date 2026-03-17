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

# Canonical Fact query structure — all 16 columns matching row_to_fact contract
FACT_COLUMNS = (
    "f.id, f.tenant_id, f.project, f.content, f.fact_type, f.tags, f.metadata, "
    "f.hash, f.valid_from, f.valid_until, f.source, f.confidence, "
    "f.created_at, f.updated_at, f.is_tombstoned, f.is_quarantined"
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

        Builds the dict directly from the row tuple — no intermediate Fact
        allocation. Columns must match FACT_COLUMNS order (16 columns).
        """
        import json

        from cortex.crypto import get_default_encrypter

        enc = get_default_encrypter()
        r = list(row)
        while len(r) < 16:
            r.append(None)

        db_tenant_id = r[1] or "default"

        # Decrypt content
        try:
            content = enc.decrypt_str(r[3], tenant_id=db_tenant_id) if r[3] else ""
        except ValueError:
            content = f"[ENCRYPTED — decryption failed] (fact #{r[0]})"

        # Parse tags
        try:
            tags = json.loads(r[5]) if r[5] else []
        except (json.JSONDecodeError, TypeError):
            tags = []

        # Decrypt meta
        try:
            meta = enc.decrypt_json(r[6], tenant_id=db_tenant_id) if r[6] else {}
        except ValueError:
            meta = {"error": "decryption_failed", "fact_id": r[0]}

        return {
            "id": r[0],
            "tenant_id": db_tenant_id,
            "project": r[2],
            "content": content,
            "fact_type": r[4],
            "type": r[4],  # API compat alias
            "tags": tags,
            "confidence": r[11] or (meta.get("confidence", "C5") if meta else "C5"),
            "valid_from": r[8] or (meta.get("valid_from") if meta else r[12]),
            "valid_until": "9999-12-31T23:59:59Z" if bool(r[14]) else r[9],
            "source": r[10] or (meta.get("source", "system") if meta else "system"),
            "meta": meta,
            "consensus_score": meta.get("consensus_score", 1.0) if meta else 1.0,
            "created_at": r[12],
            "updated_at": r[13],
            "tx_id": meta.get("tx_id") if meta else None,
            "parent_decision_id": meta.get("parent_decision_id") if meta else None,
            "hash": r[7],
        }

    def _resolve_tenant(self, tenant_id: str) -> str:
        """Resolve and validate the tenant ID from context if 'default' is provided."""
        if tenant_id == "default":
            from cortex.extensions.security.tenant import get_tenant_id

            tenant_id = get_tenant_id()

        # Strict Multi-Tenancy (RLS): Never allow empty tenant
        if not tenant_id:
            tenant_id = "default"

        return tenant_id
