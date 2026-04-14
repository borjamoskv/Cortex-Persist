"""CORTEX Health Index — FastAPI routes.

Provides /v1/health/check, /v1/health/report, /v1/health/score,
/v1/health/metrics, /v1/health/prometheus, /v1/health/history
powered by the Health Index engine.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from cortex.extensions.health import HealthCollector, HealthScorer
from cortex.extensions.health.models import HealthReport, HealthThresholds

router = APIRouter(prefix="/v1/health", tags=["health-index"])
MAX_PUBLIC_HISTORY_LIMIT = 100


@router.get("/check")
async def health_index_check(request: Request) -> dict:
    """Quick health check — score, grade, healthy boolean."""
    db_path = _get_db_path(request)
    collector = HealthCollector(db_path=db_path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    return {
        "healthy": hs.score >= 40.0,
        "score": round(hs.score, 2),
        "grade": hs.grade.letter,
        "summary": HealthScorer.summarize(hs),
    }


@router.get("/score")
async def health_index_score(request: Request) -> dict:
    """Numeric score only (0-100)."""
    db_path = _get_db_path(request)
    collector = HealthCollector(db_path=db_path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    return {"score": round(hs.score, 2), "grade": hs.grade.letter}


@router.get("/report")
async def health_index_report(request: Request) -> dict:
    """Full health report with recommendations and warnings."""
    db_path = _get_db_path(request)
    collector = HealthCollector(db_path=db_path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    t = HealthThresholds()

    recommendations: list[str] = []
    warnings: list[str] = []

    for m in hs.metrics:
        if m.value < t.critical:
            warnings.append(f"{m.name}: CRITICAL ({m.value:.0%})")
        elif m.value < t.degraded:
            warnings.append(f"{m.name}: degraded ({m.value:.0%})")
        elif m.value < t.improve:
            recommendations.append(f"{m.name}: could improve ({m.value:.0%})")

    if hs.score < 40:
        warnings.append(f"Overall health DEGRADED ({hs.grade.letter})")
    elif hs.score < 70:
        recommendations.append("Run cortex compact to reduce entropy")

    report = HealthReport(
        score=hs,
        recommendations=recommendations,
        warnings=warnings,
        # The health surface is intentionally public; never expose internal filesystem paths.
        db_path="",
    )
    return report.to_dict()


@router.get("/metrics")
async def health_index_metrics(request: Request) -> dict:
    """Public health summary without exposing collector internals."""
    db_path = _get_db_path(request)
    collector = HealthCollector(db_path=db_path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    return {
        "healthy": hs.score >= 40.0,
        "score": round(hs.score, 2),
        "grade": hs.grade.letter,
        "collector_count": len(metrics),
    }


@router.get("/prometheus")
async def health_index_prometheus(request: Request):
    """Prometheus text exposition format."""
    from fastapi.responses import PlainTextResponse

    from cortex.extensions.health.prometheus import export_prometheus

    db_path = _get_db_path(request)
    collector = HealthCollector(db_path=db_path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    content = export_prometheus(hs, include_sub_indices=False, include_collectors=False)
    return PlainTextResponse(content=content, media_type="text/plain")


@router.get("/history")
async def health_index_history(
    request: Request,
    limit: int = Query(20, ge=1, le=MAX_PUBLIC_HISTORY_LIMIT),
) -> dict:
    """Persisted health score history."""
    from cortex.extensions.health.trend import TrendDetector

    db_path = _get_db_path(request)
    normalized_limit = max(1, min(limit, MAX_PUBLIC_HISTORY_LIMIT))
    records = TrendDetector.query_history(db_path, limit=normalized_limit)
    return {"history": records, "count": len(records)}


def _get_db_path(request: Request) -> str:
    """Extract DB path from the running engine."""
    try:
        engine = getattr(request.app.state, "engine", None)
        if engine:
            return str(getattr(engine, "_db_path", ""))
    except Exception:  # noqa: BLE001
        pass
    return ""
