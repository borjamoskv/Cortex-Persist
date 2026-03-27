"""Engine Mixin Base — The sovereign foundation for all engine sub-layers.
Ω₂: Thermodynamic optimization via shared abstractions.
"""

from __future__ import annotations

import json
import logging
import types
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite

from cortex.crypto import get_default_encrypter
from cortex.engine.self_assembly import SelfAssemblyEngine

__all__ = ["EngineMixinBase"]

logger = logging.getLogger("cortex.engine")

_autopoiesis = SelfAssemblyEngine()

# Canonical Fact query structure — append-only to preserve older tuple offsets
FACT_COLUMNS = (
    "f.id, f.tenant_id, f.project, f.content, f.fact_type, f.tags, f.metadata, "
    "f.hash, f.valid_from, f.valid_until, f.source, f.confidence, "
    "f.created_at, f.updated_at, f.is_tombstoned, f.is_quarantined, "
    "f.consensus_score, f.last_accessed, f.tx_id, f.cognitive_layer, "
    "f.parent_decision_id"
)
FACT_INDEX = {col.split(".")[-1].strip(): i for i, col in enumerate(FACT_COLUMNS.split(","))}
FACT_JOIN = "FROM facts f"


class EngineMixinBase:
    """Base class for all Engine Mixins to share core database and security logic."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Ω₁₀ Autopoietic Subclassing: Wrap all new public methods for AST evolution
        for attr_name, attr_value in cls.__dict__.items():
            if not attr_name.startswith("_") and isinstance(attr_value, types.FunctionType):
                wrapped = _autopoiesis.observe_and_mutate(attr_value)
                setattr(cls, attr_name, wrapped)

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
        self,
        conn: aiosqlite.Connection,
        project: str,
        action: str,
        details: dict[str, Any],
        tenant_id: str = "default",
    ) -> int:
        """Log a transaction to the ledger."""
        raise NotImplementedError

    async def search(self, *args, **kwargs) -> Any:
        """Perform hybrid search."""
        raise NotImplementedError

    def _row_to_fact(self, row: dict | aiosqlite.Row, tenant_id: str) -> dict[str, Any]:
        """Convert a database row to a decrypted fact dictionary (Ω₂).

        Uses FACT_INDEX to ensure O(1) attribute mapping without magic numbers.
        """
        enc = get_default_encrypter()
        r = list(row)

        # Ensure row has enough columns for the current schema
        while len(r) < len(FACT_INDEX):
            r.append(None)

        idx = FACT_INDEX
        db_tenant_id = r[idx["tenant_id"]] or "default"

        # Decrypt primary payload
        try:
            content = (
                enc.decrypt_str(r[idx["content"]], tenant_id=db_tenant_id)
                if r[idx["content"]]
                else ""
            )
        except (ValueError, TypeError):
            content = f"[ENCRYPTED — decryption failed] (fact #{r[idx['id']]})"

        # Parse tags
        try:
            raw_tags = r[idx["tags"]]
            tags = json.loads(raw_tags) if raw_tags else []
        except (json.JSONDecodeError, TypeError):
            tags = []

        # Decrypt metadata
        try:
            raw_meta = r[idx["metadata"]]
            meta = enc.decrypt_json(raw_meta, tenant_id=db_tenant_id) if raw_meta else {}
        except (ValueError, TypeError):
            meta = {"error": "decryption_failed", "fact_id": r[idx["id"]]}

        # Resolution for derived/shadowed attributes
        consensus_score = r[idx["consensus_score"]]
        if consensus_score is None:
            consensus_score = meta.get("consensus_score", 1.0) if meta else 1.0

        tx_id = r[idx["tx_id"]]
        if tx_id is None and meta:
            tx_id = meta.get("tx_id")

        cognitive_layer = r[idx["cognitive_layer"]]
        if not cognitive_layer:
            cognitive_layer = meta.get("cognitive_layer", "semantic") if meta else "semantic"

        parent_id = r[idx["parent_decision_id"]]
        if parent_id is None and meta:
            parent_id = meta.get("parent_decision_id")

        return {
            "id": r[idx["id"]],
            "tenant_id": db_tenant_id,
            "project": r[idx["project"]],
            "content": content,
            "fact_type": r[idx["fact_type"]],
            "type": r[idx["fact_type"]],  # Legacy compatibility alias
            "tags": tags,
            "confidence": r[idx["confidence"]] or (meta.get("confidence", "Ω5") if meta else "Ω5"),
            "valid_from": r[idx["valid_from"]]
            or (meta.get("valid_from") if meta else r[idx["created_at"]]),
            "valid_until": "9999-12-31T23:59:59Z"
            if bool(r[idx["is_tombstoned"]])
            else r[idx["valid_until"]],
            "source": r[idx["source"]] or (meta.get("source", "system") if meta else "system"),
            "meta": meta,
            "consensus_score": consensus_score,
            "last_accessed": r[idx["last_accessed"]],
            "created_at": r[idx["created_at"]],
            "updated_at": r[idx["updated_at"]],
            "tx_id": tx_id,
            "cognitive_layer": cognitive_layer,
            "parent_decision_id": parent_id,
            "hash": r[idx["hash"]],
            "is_quarantined": bool(r[idx["is_quarantined"]]),
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
