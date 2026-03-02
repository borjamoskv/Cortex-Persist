"""History and Time-Travel Mixin for AsyncCortexEngine."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN, EngineMixinBase

logger = logging.getLogger("cortex.engine.history")


class HistoryMixin(EngineMixinBase):
    """Mixin for history and time-travel logic in AsyncCortexEngine."""

    async def time_travel(self, tx_id: int, project: str | None = None) -> list[dict[str, Any]]:
        """Reconstruct state as of transaction ID."""
        from cortex.memory.temporal import time_travel_filter
        from cortex.security.tenant import get_tenant_id

        current_tenant = get_tenant_id()

        async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
            from cortex.crypto import get_default_encrypter

            enc = get_default_encrypter()

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
                    d = dict(row)
                    d["content"] = (
                        enc.decrypt_str(d["content"], tenant_id=current_tenant)
                        if d.get("content")
                        else ""
                    )
                    d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
                    d["meta"] = (
                        enc.decrypt_json(d["meta"], tenant_id=current_tenant)
                        if d.get("meta")
                        else {}
                    )
                    results.append(d)
                return results

    async def reconstruct_state(
        self, tx_id: int, project: str | None = None
    ) -> list[dict[str, Any]]:
        """Alias for time_travel."""
        return await self.time_travel(tx_id, project)
