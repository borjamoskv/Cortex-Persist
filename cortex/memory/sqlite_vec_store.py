# [C5-REAL] Exergy-Maximized
"""
Sovereign Vector Store (SQLite-Vec).

Zero-Trust, Multi-Tenant Semantic Memory backed by sqlite-vec.
Enforces partition by tenant_id and incorporates OUROBOROS success_rate
and temporal decay directly in the embedding retrieval.
"""

# This module uses validated dynamic sqlite identifiers for tenant/project sharded tables.

from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

from cortex.memory.encoder import AsyncEncoder

__all__ = ["SovereignVectorStoreL2"]

# Lazy imports to avoid circular deps at module load
# L2HybridSearch and PIISanitizer only needed at runtime
_L2_HYBRID_SEARCH_AVAILABLE: bool | None = None  # None = not yet checked

logger = logging.getLogger("cortex.memory.sqlite_vec_store")


from cortex.memory.traits.read import ReadTrait
from cortex.memory.traits.schema import SchemaTrait
from cortex.memory.traits.write import WriteTrait


class SovereignVectorStoreL2(SchemaTrait, ReadTrait, WriteTrait):
    """Async vector store for CORTEX v6 L2 semantic memory.

    Uses `sqlite-vec` for extremely fast, local, zero-trust vector recall.
    Calculates final scores based on Cosine Similarity, Temporal Decay,
    and OUROBOROS success_rate.
    """

    __slots__ = (
        "_conn",
        "_db_path",
        "_encoder",
        "_half_life",
        "_hybrid",
        "_lock",
        "_ready",
        "_sanitizer",
        "_vector_enabled",
    )

    MAX_DOMAIN_ENTROPY = 5000  # Axiom Ω8: Critical mass for Universe Splitting

    def __init__(
        self,
        encoder: AsyncEncoder,
        db_path: str | Path = "~/.cortex/vectors.db",
        half_life_days: int = 7,
    ) -> None:
        self._encoder = encoder
        db_path_obj = Path(db_path).expanduser()
        self._db_path = str(db_path_obj)
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()
        self._ready = False
        self._half_life = half_life_days * 24 * 3600
        self._vector_enabled = False
        # Lazy-initialized subsystems
        self._hybrid = None  # L2HybridSearch - created after conn is ready
        self._sanitizer = None  # PIISanitizer singleton

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                self._ready = False
