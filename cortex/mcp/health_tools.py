"""MCP tools for CORTEX Health Index.

Registers health monitoring tools on a FastMCP server so AI agents
can query system health autonomously.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("cortex.mcp.health")


def register_health_tools(mcp: Any, ctx: Any) -> None:
    """Register health tools on the MCP server.

    Args:
        mcp: FastMCP server instance.
        ctx: MCPContext with engine reference.
    """

    @mcp.tool()
    async def cortex_health_check() -> dict:
        """Quick CORTEX health check — returns score, grade, and healthy boolean.

        No arguments required. Checks DB, ledger, and entropy.
        Returns: {"healthy": bool, "score": float, "grade": str}
        """
        from cortex.health import HealthCollector, HealthScorer

        db_path = getattr(ctx, "db_path", "")
        collector = HealthCollector(db_path=db_path)
        metrics = collector.collect_all()
        hs = HealthScorer.score(metrics)

        return {
            "healthy": hs.score >= 40.0,
            "score": round(hs.score, 2),
            "grade": hs.grade,
            "summary": HealthScorer.summarize(hs),
            "metrics": [
                {
                    "name": m.name,
                    "value": round(m.value, 4),
                    "weight": m.weight,
                }
                for m in hs.metrics
            ],
        }

    @mcp.tool()
    async def cortex_health_report() -> dict:
        """Full CORTEX health report with score, recommendations, and warnings.

        No arguments required.
        Returns: {"score": {...}, "recommendations": [...], "warnings": [...]}
        """
        from cortex.health import HealthCollector, HealthScorer
        from cortex.health.models import HealthReport

        db_path = getattr(ctx, "db_path", "")
        collector = HealthCollector(db_path=db_path)
        metrics = collector.collect_all()
        hs = HealthScorer.score(metrics)

        recommendations: list[str] = []
        warnings: list[str] = []

        for m in hs.metrics:
            if m.value < 0.5:
                warnings.append(
                    f"{m.name}: critical ({m.value:.2f})"
                )
            elif m.value < 0.8:
                recommendations.append(
                    f"{m.name}: could improve ({m.value:.2f})"
                )

        if hs.score < 40:
            warnings.append(
                f"Overall health DEGRADED ({hs.grade})"
            )
        elif hs.score < 70:
            recommendations.append(
                "Run cortex compact to reduce entropy"
            )

        report = HealthReport(
            score=hs,
            recommendations=recommendations,
            warnings=warnings,
            db_path=str(db_path),
        )
        return report.to_dict()

    logger.debug("Registered health MCP tools")
