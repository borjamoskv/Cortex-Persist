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
    "f.id, f.tenant_id, f.project, f.content, f.fact_type, f.tags, f.confidence, "
    "f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, "
    "f.created_at, f.updated_at, f.tx_id, t.hash"
)
FACT_JOIN = "FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id"


class EngineMixinBase:
    """Base class for all Engine Mixins to share core database and security logic."""

    @asynccontextmanager
    async def session(self) -> AsyncIterator[aiosqlite.Connection]:
        """Provide a transactional session from the connection pool."""
        # This will be implemented by AsyncCortexEngine
        raise NotImplementedError("Mixins must be used with a class that implements session()")

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
            "confidence": fact.confidence,
            "valid_from": fact.valid_from,
            "valid_until": fact.valid_until,
            "source": fact.source,
            "meta": fact.meta,
            "consensus_score": fact.consensus_score,
            "created_at": fact.created_at,
            "updated_at": fact.updated_at,
            "tx_id": fact.tx_id,
            "hash": fact.hash,
        }
