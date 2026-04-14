from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.requests import Request

from cortex.extensions.health.models import Grade, HealthScore, MetricSnapshot
from cortex.extensions.health import trend as health_trend
from cortex.routes import health as health_routes


def _make_request(db_path: str = "/tmp/secret-cortex.db") -> Request:
    app = FastAPI()
    app.state.engine = SimpleNamespace(_db_path=db_path)
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/v1/health/report",
            "headers": [],
            "query_string": b"",
            "app": app,
        }
    )


def test_health_report_redacts_db_path(monkeypatch) -> None:
    class _Collector:
        def __init__(self, db_path: str) -> None:
            self.db_path = db_path

        def collect_all(self):
            return [MetricSnapshot(name="entropy", value=0.82)]

    def _score(metrics):
        return HealthScore(score=78.0, grade=Grade.GOOD, metrics=metrics)

    monkeypatch.setattr(health_routes, "HealthCollector", _Collector)
    monkeypatch.setattr(health_routes.HealthScorer, "score", _score)

    report = asyncio.run(health_routes.health_index_report(_make_request()))

    assert report["db_path"] == ""
    assert report["score"]["grade"] == "B"


def test_health_metrics_redacts_collector_details(monkeypatch) -> None:
    class _Collector:
        def __init__(self, db_path: str) -> None:
            self.db_path = db_path

        def collect_all(self):
            return [
                MetricSnapshot(
                    name="entropy",
                    value=0.82,
                    latency_ms=12.5,
                    description="sensitive",
                    remediation="do-not-leak",
                )
            ]

    def _score(metrics):
        return HealthScore(score=78.0, grade=Grade.GOOD, metrics=metrics)

    monkeypatch.setattr(health_routes, "HealthCollector", _Collector)
    monkeypatch.setattr(health_routes.HealthScorer, "score", _score)

    payload = asyncio.run(health_routes.health_index_metrics(_make_request()))

    assert payload == {
        "healthy": True,
        "score": 78.0,
        "grade": "B",
        "collector_count": 1,
    }


def test_health_prometheus_redacts_collector_metrics(monkeypatch) -> None:
    class _Collector:
        def __init__(self, db_path: str) -> None:
            self.db_path = db_path

        def collect_all(self):
            return [MetricSnapshot(name="entropy", value=0.82, latency_ms=12.5)]

    def _score(metrics):
        return HealthScore(score=78.0, grade=Grade.GOOD, metrics=metrics, sub_indices={"storage": 91})

    monkeypatch.setattr(health_routes, "HealthCollector", _Collector)
    monkeypatch.setattr(health_routes.HealthScorer, "score", _score)

    response = asyncio.run(health_routes.health_index_prometheus(_make_request()))

    assert isinstance(response, PlainTextResponse)
    body = response.body.decode("utf-8")
    assert "cortex_health_score_total 78.00" in body
    assert "cortex_health_grade 3" in body
    assert "cortex_health_metric_value" not in body
    assert "cortex_health_metric_latency_ms" not in body
    assert "cortex_health_sub_index" not in body


def test_health_history_caps_limit(monkeypatch) -> None:
    seen: dict[str, int] = {}

    def _query_history(db_path: str, limit: int = 20):
        seen["limit"] = limit
        return [{"timestamp": "2026-04-14T00:00:00+00:00", "score": 78.0, "grade": "B"}]

    monkeypatch.setattr(health_trend.TrendDetector, "query_history", staticmethod(_query_history))

    payload = asyncio.run(health_routes.health_index_history(_make_request(), limit=9999))

    assert seen["limit"] == health_routes.MAX_PUBLIC_HISTORY_LIMIT
    assert payload["count"] == 1
