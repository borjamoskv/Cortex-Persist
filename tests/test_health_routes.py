from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi import FastAPI
from starlette.requests import Request

from cortex.extensions.health.models import Grade, HealthScore, MetricSnapshot
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
