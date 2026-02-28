"""Memory Scanner — Extracts frequency distributions from CORTEX SQLite.

Async bridge between the CortexEngine and the pure-math Shannon analyzer.
Each method runs a single GROUP BY query and returns a dict[str, int]
frequency distribution ready for entropy analysis.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

__all__ = ["MemoryScanner"]

logger = logging.getLogger("cortex.shannon")

# Age bucket boundaries in days
_AGE_BUCKETS = [
    ("today", 1),
    ("this_week", 7),
    ("this_month", 30),
    ("this_quarter", 90),
    ("older", None),
]

# Base WHERE clause for active (non-deprecated, non-quarantined) facts
_ACTIVE = "valid_until IS NULL AND is_quarantined = 0"
_PROJECT_FILTER = " AND project = ?"


class MemoryScanner:
    """Extracts frequency distributions from the CORTEX fact store."""

    __slots__ = ("_engine",)

    def __init__(self, engine: CortexEngine) -> None:
        self._engine = engine

    # ── Single-dimension distributions ──────────────────────────────

    async def type_distribution(
        self, project: str | None = None,
    ) -> dict[str, int]:
        """Frequency of each fact_type among active facts."""
        return await self._grouped_count("fact_type", project)

    async def confidence_distribution(
        self, project: str | None = None,
    ) -> dict[str, int]:
        """Frequency of each confidence level among active facts."""
        return await self._grouped_count("confidence", project)

    async def project_distribution(self) -> dict[str, int]:
        """Frequency of active facts per project."""
        return await self._grouped_count("project", project=None)

    async def source_distribution(
        self, project: str | None = None,
    ) -> dict[str, int]:
        """Frequency of active facts per source."""
        return await self._grouped_count("source", project)

    async def age_distribution(
        self, project: str | None = None,
    ) -> dict[str, int]:
        """Active facts bucketed by age (today/week/month/quarter/older)."""
        where = _ACTIVE
        params: list[str] = []
        if project:
            where += _PROJECT_FILTER
            params.append(project)

        async with self._engine.session() as conn:
            result: dict[str, int] = {}
            for label, days in _AGE_BUCKETS:
                if days is not None:
                    q = (
                        f"SELECT COUNT(*) FROM facts WHERE {where} "
                        f"AND created_at >= datetime('now', '-{days} days')"
                    )
                else:
                    q = (
                        f"SELECT COUNT(*) FROM facts WHERE {where} "
                        "AND created_at < datetime('now', '-90 days')"
                    )
                cursor = await conn.execute(q, params)
                row = await cursor.fetchone()
                count = row[0] if row else 0
                if count > 0:
                    result[label] = count
            return result

    # ── Joint distribution (for mutual information) ──────────────────

    async def type_project_joint(self) -> dict[tuple[str, str], int]:
        """Joint distribution of (fact_type, project) for I(type; project)."""
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT fact_type, project, COUNT(*) "
                f"FROM facts WHERE {_ACTIVE} "
                "GROUP BY fact_type, project"
            )
            rows = await cursor.fetchall()
            return {(r[0], r[1]): r[2] for r in rows}

    # ── Temporal velocity (trend detection) ──────────────────────────

    async def temporal_velocity(
        self,
        project: str | None = None,
        window_days: int = 30,
    ) -> dict[str, int]:
        """Facts created per day for the last `window_days` days.

        Returns:
            Mapping of ISO date string → fact count for that day.
            Only days with at least 1 fact are included.
        """
        where = _ACTIVE
        params: list[object] = [window_days]
        if project:
            where += _PROJECT_FILTER
            params.append(project)

        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT DATE(created_at) AS day, COUNT(*) "
                f"FROM facts WHERE {where} "
                "AND created_at >= datetime('now', '-' || ? || ' days') "
                "GROUP BY day ORDER BY day",
                params,
            )
            rows = await cursor.fetchall()
            return {r[0]: r[1] for r in rows if r[0] is not None}

    # ── Content length distribution ──────────────────────────────────

    async def content_length_distribution(
        self, project: str | None = None,
    ) -> dict[str, int]:
        """Content length bucketed into bands for quality assessment.

        Bands: micro (<20), short (20-50), medium (50-150),
               long (150-500), extensive (>500).
        """
        where = _ACTIVE
        params: list[str] = []
        if project:
            where += _PROJECT_FILTER
            params.append(project)

        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT "
                "  CASE "
                "    WHEN LENGTH(content) < 20 THEN 'micro' "
                "    WHEN LENGTH(content) < 50 THEN 'short' "
                "    WHEN LENGTH(content) < 150 THEN 'medium' "
                "    WHEN LENGTH(content) < 500 THEN 'long' "
                "    ELSE 'extensive' "
                "  END AS band, "
                "  COUNT(*) "
                f"FROM facts WHERE {where} "
                "GROUP BY band",
                params,
            )
            rows = await cursor.fetchall()
            return {r[0]: r[1] for r in rows}

    # ── Totals ───────────────────────────────────────────────────────

    async def total_active_facts(
        self, project: str | None = None,
    ) -> int:
        """Count of active (non-deprecated, non-quarantined) facts."""
        where = _ACTIVE
        params: list[str] = []
        if project:
            where += _PROJECT_FILTER
            params.append(project)

        async with self._engine.session() as conn:
            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM facts WHERE {where}", params,
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    # ── Internal helpers ─────────────────────────────────────────────

    async def _grouped_count(
        self, column: str, project: str | None,
    ) -> dict[str, int]:
        """Generic GROUP BY count for a single column."""
        where = _ACTIVE
        params: list[str] = []
        if project:
            where += _PROJECT_FILTER
            params.append(project)

        async with self._engine.session() as conn:
            cursor = await conn.execute(
                f"SELECT {column}, COUNT(*) FROM facts "
                f"WHERE {where} GROUP BY {column}",
                params,
            )
            rows = await cursor.fetchall()
            return {
                (str(r[0]) if r[0] is not None else "unknown"): r[1]
                for r in rows
            }
