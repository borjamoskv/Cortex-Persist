"""Cognitive Fingerprint — Raw pattern queries from CORTEX SQLite.

Async bridge between the engine and the preference extractor.
Each method runs a focused SQL query and returns structured raw data.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

__all__ = ["FingerprintScanner"]

logger = logging.getLogger("cortex.extensions.fingerprint")

# Active facts WHERE clause (mirrors shannon/scanner.py convention)
_ACTIVE = "valid_until IS NULL AND is_quarantined = 0"
_PROJECT_FILTER = " AND project = ?"

# Confidence → weight mapping
_CONF_WEIGHTS: dict[str, float] = {
    "C5": 1.0,
    "C4": 0.8,
    "C3": 0.6,
    "C2": 0.4,
    "C1": 0.2,
}


class FingerprintScanner:
    """Extracts behavioral pattern data from the CORTEX fact store."""

    __slots__ = ("_engine",)

    def __init__(self, engine: CortexEngine) -> None:
        self._engine = engine

    async def confidence_distribution(
        self,
        project: Optional[str] = None,
    ) -> dict[str, int]:
        """Count facts per confidence level."""
        return await self._grouped_count("confidence", project)

    async def fact_type_distribution(
        self,
        project: Optional[str] = None,
    ) -> dict[str, int]:
        """Count facts per fact_type."""
        return await self._grouped_count("fact_type", project)

    async def total_facts(
        self,
        project: Optional[str] = None,
    ) -> int:
        """Count all active facts."""
        where, params = self._where(project)
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM facts WHERE {where}",
                params,  # nosec B608
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def distinct_projects(self) -> int:
        """Number of distinct projects with active facts."""
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                f"SELECT COUNT(DISTINCT project) FROM facts WHERE {_ACTIVE}"  # nosec B608
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def avg_content_length(
        self,
        project: Optional[str] = None,
    ) -> float:
        """Average character length of fact content."""
        where, params = self._where(project)
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                f"SELECT AVG(LENGTH(content)) FROM facts WHERE {where}",  # nosec B608
                params,
            )
            row = await cursor.fetchone()
            return float(row[0]) if row and row[0] else 0.0

    async def recency_ratio(
        self,
        project: Optional[str] = None,
        recent_days: int = 30,
    ) -> tuple[int, int]:
        """Facts in last N days vs total — measures recency bias.

        Returns:
            (recent_count, total_count)
        """
        where, params = self._where(project)
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM facts WHERE {where} "  # nosec B608
                "AND created_at >= datetime('now', '-' || ? || ' days')",
                (*params, recent_days),
            )
            row = await cursor.fetchone()
            recent = row[0] if row else 0

            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM facts WHERE {where}",
                params,  # nosec B608
            )
            row = await cursor.fetchone()
            total = row[0] if row else 0

            return recent, max(total, 1)

    async def active_days(
        self,
        project: Optional[str] = None,
    ) -> tuple[int, float]:
        """Number of distinct days with ≥1 fact and total span in days.

        Returns:
            (active_day_count, total_span_days)
        """
        where, params = self._where(project)
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT DATE(created_at) AS d "  # nosec B608
                f"FROM facts WHERE {where} GROUP BY d ORDER BY d",
                params,
            )
            rows = await cursor.fetchall()
            if not rows:
                return 0, 0.0

            from datetime import date as dt_date

            days = [dt_date.fromisoformat(r[0]) for r in rows if r[0]]
            if len(days) < 2:
                return len(days), 1.0
            span = float((days[-1] - days[0]).days) or 1.0
            return len(days), span

    async def domain_profiles(
        self,
        project: Optional[str] = None,
        top_n: int = 20,
    ) -> list[dict]:
        """Per-(project, fact_type) profile: count, avg content len, last seen, source.

        Returns:
            List of dicts with keys: project, fact_type, count, avg_len,
            last_seen_days_ago, dominant_source.
        """
        where, params = self._where(project)
        async with self._engine.session() as conn:
            # Main aggregation
            cursor = await conn.execute(
                "SELECT project, fact_type, COUNT(*) AS cnt, "  # nosec B608
                "AVG(LENGTH(content)) AS avg_len, "
                "MAX(created_at) AS last_seen "
                f"FROM facts WHERE {where} "
                "GROUP BY project, fact_type "
                "ORDER BY cnt DESC LIMIT ?",
                (*params, top_n),
            )
            rows = await cursor.fetchall()
            profiles = []
            for row in rows:
                proj, ftype, cnt, avg_len, last_seen = row

                # Dominant source for this domain
                cursor2 = await conn.execute(
                    "SELECT source, COUNT(*) AS c "  # nosec B608
                    f"FROM facts WHERE {where} AND project = ? AND fact_type = ? "
                    "GROUP BY source ORDER BY c DESC LIMIT 1",
                    (*params, proj, ftype),
                )
                src_row = await cursor2.fetchone()
                dominant_source = src_row[0] if src_row else "unknown"

                # Days since last fact in this domain
                cursor3 = await conn.execute(
                    "SELECT CAST("  # nosec B608
                    "julianday('now') - julianday(?) AS REAL)",
                    (last_seen,),
                )
                age_row = await cursor3.fetchone()
                recency_days = float(age_row[0]) if age_row and age_row[0] else 0.0

                # Confidence distribution for this domain
                cursor4 = await conn.execute(
                    "SELECT confidence, COUNT(*) "  # nosec B608
                    f"FROM facts WHERE {where} AND project = ? AND fact_type = ? "
                    "GROUP BY confidence",
                    (*params, proj, ftype),
                )
                conf_rows = await cursor4.fetchall()
                weighted = sum(_CONF_WEIGHTS.get(str(c), 0.3) * n for c, n in conf_rows)
                avg_conf = weighted / max(cnt, 1)

                profiles.append(
                    {
                        "project": proj,
                        "fact_type": ftype,
                        "count": cnt,
                        "avg_len": float(avg_len or 0),
                        "recency_days": recency_days,
                        "dominant_source": dominant_source or "unknown",
                        "avg_confidence_weight": avg_conf,
                    }
                )
            return profiles

    async def weekly_velocity_per_domain(
        self,
        project: Optional[str] = None,
    ) -> dict[tuple[str, str], float]:
        """Facts per week for each (project, fact_type) pair."""
        where, params = self._where(project)
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT project, fact_type, COUNT(*) AS cnt, "  # nosec B608
                "MAX(julianday('now') - julianday(created_at)) AS span_days "
                f"FROM facts WHERE {where} GROUP BY project, fact_type",
                params,
            )
            rows = await cursor.fetchall()
            result: dict[tuple[str, str], float] = {}
            for proj, ftype, cnt, span in rows:
                weeks = max(float(span or 7) / 7.0, 1.0)
                result[(proj, ftype)] = round(cnt / weeks, 2)
            return result

    # ── Internal ─────────────────────────────────────────────────

    def _where(self, project: Optional[str]) -> tuple[str, list]:
        """Build WHERE clause and params."""
        where = _ACTIVE
        params: list = []
        if project:
            where += _PROJECT_FILTER
            params.append(project)
        return where, params

    async def _grouped_count(
        self,
        column: str,
        project: Optional[str],
    ) -> dict[str, int]:
        """Generic GROUP BY COUNT for a single column."""
        where, params = self._where(project)
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                f"SELECT {column}, COUNT(*) FROM facts "  # nosec B608
                f"WHERE {where} GROUP BY {column}",
                params,
            )
            rows = await cursor.fetchall()
            return {(str(r[0]) if r[0] is not None else "unknown"): r[1] for r in rows}
