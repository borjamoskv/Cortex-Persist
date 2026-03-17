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

logger = logging.getLogger("cortex.extensions.shannon")

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
        self,
        project: str | None = None,
    ) -> dict[str, int]:
        """Frequency of each fact_type among active facts."""
        return await self._grouped_count("fact_type", project)

    async def confidence_distribution(
        self,
        project: str | None = None,
    ) -> dict[str, int]:
        """Frequency of each confidence level among active facts."""
        return await self._grouped_count("confidence", project)

    async def project_distribution(self) -> dict[str, int]:
        """Frequency of active facts per project."""
        return await self._grouped_count("project", project=None)

    async def source_distribution(
        self,
        project: str | None = None,
    ) -> dict[str, int]:
        """Frequency of active facts per source."""
        return await self._grouped_count("source", project)

    async def age_distribution(
        self,
        project: str | None = None,
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
                # Use parameterized '-' || ? || ' days' to avoid injecting
                # integer literals directly into SQL (bandit B608).
                if days is not None:
                    q = (
                        f"SELECT COUNT(*) FROM facts WHERE {where} "  # nosec B608
                        "AND created_at >= datetime('now', '-' || ? || ' days')"
                    )
                    row_params = (*params, days)
                else:
                    q = (
                        f"SELECT COUNT(*) FROM facts WHERE {where} "  # nosec B608
                        "AND created_at < datetime('now', '-' || ? || ' days')"
                    )
                    row_params = (*params, 90)
                cursor = await conn.execute(q, row_params)
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
                "SELECT fact_type, project, COUNT(*) "  # nosec B608 — parameterized query — {where}/{column}/{placeholders} built internally with ? params
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
                "SELECT DATE(created_at) AS day, COUNT(*) "  # nosec B608 — parameterized query — {where}/{column}/{placeholders} built internally with ? params
                f"FROM facts WHERE {where} "
                "AND created_at >= datetime('now', '-' || ? || ' days') "
                "GROUP BY day ORDER BY day",
                params,
            )
            rows = await cursor.fetchall()
            return {r[0]: r[1] for r in rows if r[0] is not None}

    # ── Content length distribution ──────────────────────────────────

    async def content_length_distribution(
        self,
        project: str | None = None,
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
                "SELECT "  # nosec B608 — parameterized query — {where}/{column}/{placeholders} built internally with ? params
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
        self,
        project: str | None = None,
    ) -> int:
        """Count of active (non-deprecated, non-quarantined) facts."""
        where = _ACTIVE
        params: list[str] = []
        if project:
            where += _PROJECT_FILTER
            params.append(project)

        async with self._engine.session() as conn:
            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM facts WHERE {where}",
                params,  # nosec B608 — parameterized query — {where}/{column}/{placeholders} built internally with ? params
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    # ── Immortality Index queries ───────────────────────────────────

    async def domain_coverage(self) -> tuple[int, int]:
        """Filled vs. theoretical max (fact_type × project) pairs.

        Returns:
            (filled_pairs, theoretical_max) — coverage = filled / max.
        """
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(DISTINCT fact_type || '::' || project) "  # nosec B608
                f"FROM facts WHERE {_ACTIVE}"
            )
            row = await cursor.fetchone()
            filled = row[0] if row else 0

            cursor = await conn.execute(
                "SELECT COUNT(DISTINCT fact_type), COUNT(DISTINCT project) "  # nosec B608
                f"FROM facts WHERE {_ACTIVE}"
            )
            row = await cursor.fetchone()
            n_types = row[0] if row else 0
            n_projects = row[1] if row else 0
            theoretical = n_types * n_projects

            return filled, max(theoretical, 1)

    async def temporal_gap_days(
        self,
        project: str | None = None,
    ) -> tuple[float, float, int]:
        """Largest gap between consecutive facts and total time span.

        Returns:
            (max_gap_days, total_span_days, active_days) — continuity = 1 - max_gap/span.
        """
        where = _ACTIVE
        params: list[str] = []
        if project:
            where += _PROJECT_FILTER
            params.append(project)

        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT DATE(created_at) AS day "  # nosec B608
                f"FROM facts WHERE {where} "
                "GROUP BY day ORDER BY day",
                params,
            )
            rows = await cursor.fetchall()
            if not rows or len(rows) < 2:  # type: ignore[type-error]
                return 0.0, max(1.0, float(len(rows))), len(rows)  # type: ignore[type-error]

            from datetime import date as dt_date

            days = [dt_date.fromisoformat(r[0]) for r in rows if r[0]]
            if len(days) < 2:
                return 0.0, 1.0, len(days)

            gaps = [(days[i + 1] - days[i]).days for i in range(len(days) - 1)]
            max_gap = float(max(gaps)) if gaps else 0.0
            total_span = float((days[-1] - days[0]).days) or 1.0

            return max_gap, total_span, len(days)

    async def confidence_weight_sum(
        self,
        project: str | None = None,
    ) -> tuple[float, int]:
        """Sum of confidence-weighted facts and total count.

        Weights: C5=1.0, C4=0.8, C3=0.6, C2=0.4, C1=0.2.

        Returns:
            (weighted_sum, total_facts) — quality = weighted / total.
        """
        where = _ACTIVE
        params: list[str] = []
        if project:
            where += _PROJECT_FILTER
            params.append(project)

        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT confidence, COUNT(*) "  # nosec B608
                f"FROM facts WHERE {where} "
                "GROUP BY confidence",
                params,
            )
            rows = await cursor.fetchall()

        weights = {"C5": 1.0, "C4": 0.8, "C3": 0.6, "C2": 0.4, "C1": 0.2}
        weighted = 0.0
        total = 0
        for conf, count in rows:
            total += count
            weighted += weights.get(str(conf), 0.3) * count

        return weighted, max(total, 1)

    # ── Internal helpers ─────────────────────────────────────────────

    async def _grouped_count(
        self,
        column: str,
        project: str | None,
    ) -> dict[str, int]:
        """Generic GROUP BY count for a single column."""
        where = _ACTIVE
        params: list[str] = []
        if project:
            where += _PROJECT_FILTER
            params.append(project)

        async with self._engine.session() as conn:
            cursor = await conn.execute(
                f"SELECT {column}, COUNT(*) FROM facts "  # nosec B608 — parameterized query — {where}/{column}/{placeholders} built internally with ? params
                f"WHERE {where} GROUP BY {column}",
                params,
            )
            rows = await cursor.fetchall()
            return {(str(r[0]) if r[0] is not None else "unknown"): r[1] for r in rows}
