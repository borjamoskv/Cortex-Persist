# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
from typing import Any

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

from babylon60.engine.mixins.base import FACT_COLUMNS, FACT_JOIN, EngineMixinBase
from babylon60.extensions.security.tenant import get_tenant_id
from babylon60.memory.temporal import time_travel_filter

logger = logging.getLogger("babylon60.engine.history")


class HistoryMixin(EngineMixinBase):
    """Mixin for history and time-travel logic in AsyncCortexEngine."""

    async def time_travel(self, tx_id: int, project: str | None = None) -> list[dict[str, Any]]:
        """Reconstruct state as of transaction ID."""
        current_tenant = get_tenant_id()

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            conn.row_factory = aiosqlite.Row
            clause, params = time_travel_filter(tx_id, table_alias="f")

            # Enforce RLS
            clause = f"({clause}) AND f.tenant_id = ?"
            params.append(current_tenant)

            query = f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE {clause}"
            if project:
                query += " AND f.project = ?"
                params.append(project)
            query += " ORDER BY f.id ASC"

            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                results = []
                for row in rows:
                    # Leverage base method for secure decryption and normalization
                    fact_data = self._row_to_fact(row, current_tenant)
                    results.append(fact_data)
                return results

    async def reconstruct_state(
        self, tx_id: int, project: str | None = None
    ) -> list[dict[str, Any]]:
        """Alias for time_travel."""
        return await self.time_travel(tx_id, project)
