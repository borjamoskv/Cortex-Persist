# [C5-REAL] Exergy-Maximized
"""
L2 Drain Monitor (Turbopuffer Compaction).

Drains embeddings from sqlite-vec (HOT) to Turbopuffer (COLD)
for facts older than 7 days, maintaining true tenant isolation.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from cortex.extensions.daemon.models import CompactionAlert
from cortex.storage.qdrant import init_vector_backend
from cortex.storage.turbopuffer import TurbopufferVectorBackend

logger = logging.getLogger("moskv-daemon.l2_drain")

# 7 days in seconds
MAX_AGE_SECONDS = 7 * 24 * 3600


class L2DrainMonitor:
    """Drains vectors from L1 (SQLite-Vec) to L2 (Turbopuffer)."""

    projects: list[str]
    interval_seconds: int

    def __init__(
        self,
        projects: list[str] | None = None,
        interval_seconds: int = 28800,  # 8 hours standard sleep cycle
        engine: Any = None,
    ):
        self.projects = projects or []
        self.interval_seconds = interval_seconds
        self._last_runs: dict[str, float] = {}
        self._engine = engine
        self._backend = None

    async def _ensure_backend(self) -> bool:
        if self._backend is None:
            # Check if turbopuffer is active
            backend = await init_vector_backend()
            if not isinstance(backend, TurbopufferVectorBackend):
                return False
            self._backend = backend
        return True

    async def _drain_project(self, project: str, now: float) -> CompactionAlert | None:
        """Helper to drain a single project's cold vectors to L2."""
        last_run = self._last_runs.get(project, 0)
        if now - last_run < self.interval_seconds:
            return None

        # Verify backend
        if not await self._ensure_backend():
            return None

        drained_count = 0
        
        try:
            conn = await self._engine.get_conn()
            
            # Select facts that are HOT and updated_at is older than 7 days
            query = """
                SELECT f.id, f.tenant_id, v.embedding
                FROM facts f
                JOIN fact_embeddings v ON f.id = v.fact_id
                WHERE f.project = ?
                  AND f.storage_tier = 'HOT'
                  AND f.is_tombstoned = 0
                  AND strftime('%s', 'now') - strftime('%s', f.updated_at) > ?
                LIMIT 1000
            """
            cursor = await conn.execute(query, (project, MAX_AGE_SECONDS))
            rows = await cursor.fetchall()
            
            if not rows:
                self._last_runs[project] = now
                return None

            logger.info("L2Drain: Found %d vectors in %s to migrate to Turbopuffer.", len(rows), project)

            for fact_id, tenant_id, embedding_bytes in rows:
                cursor_json = await conn.execute("SELECT vec_to_json(?)", (embedding_bytes,))
                json_row = await cursor_json.fetchone()
                if not json_row or not json_row[0]:
                    continue
                
                embedding = json.loads(json_row[0])

                # 1. Upsert to Turbopuffer
                await self._backend.upsert(
                    fact_id=fact_id,
                    embedding=embedding,
                    tenant_id=tenant_id,
                    payload={"project": project}
                )
                
                # 2. Delete from sqlite-vec physically
                await conn.execute("DELETE FROM fact_embeddings WHERE fact_id = ?", (fact_id,))
                
                # 3. Mark as COLD
                await conn.execute("UPDATE facts SET storage_tier = 'COLD' WHERE id = ?", (fact_id,))
                
                drained_count += 1
            
            await conn.commit()
            self._last_runs[project] = now
            
            if drained_count > 0:
                return CompactionAlert(
                    project=project,
                    reduction=drained_count,
                    deprecated=0,
                    message=f"Migración L2: {drained_count} vectores movidos a Turbopuffer."
                )

        except Exception as e:
            logger.error("L2 Drain failed on %s: %s", project, e)

        return None

    async def check_async(self) -> list[CompactionAlert]:
        """Run L2 Drain asynchronously."""
        if not self.projects or not self._engine:
            return []

        alerts: list[CompactionAlert] = []
        now = time.monotonic()

        for project in self.projects:
            alert = await self._drain_project(project, now)
            if alert:
                alerts.append(alert)

        return alerts
