from __future__ import annotations

import sqlite3
from types import SimpleNamespace
from typing import Any

from cortex.routes.admin_health_probes import build_health_probes


def _make_request(cloud_backends: dict[str, Any] | None = None) -> SimpleNamespace:
    state = SimpleNamespace()
    if cloud_backends is not None:
        state.cloud_backends = cloud_backends
    app = SimpleNamespace(state=state)
    return SimpleNamespace(app=app)


def test_cloud_probes_default_unavailable_but_not_failing() -> None:
    conn = sqlite3.connect(":memory:")
    request = _make_request()
    probes = build_health_probes(conn, request, schema_version="7")

    for name in ("cloud_storage", "cloud_vector", "cloud_cache"):
        status, ok, details = probes[name]()
        assert status == "unavailable"
        assert ok is True
        assert "detail" in details

    conn.close()


def test_cloud_probes_reflect_runtime_state() -> None:
    conn = sqlite3.connect(":memory:")
    request = _make_request(
        {
            "storage": {"status": "healthy", "mode": "postgres", "detail": "connected"},
            "vector": {"status": "healthy", "backend": "qdrant", "detail": "connected"},
            "cache": {"status": "disabled", "backend": "local", "detail": "disabled"},
        }
    )
    probes = build_health_probes(conn, request, schema_version="7")

    storage_status, storage_ok, storage_details = probes["cloud_storage"]()
    assert storage_status == "healthy"
    assert storage_ok is True
    assert storage_details["mode"] == "postgres"

    vector_status, vector_ok, vector_details = probes["cloud_vector"]()
    assert vector_status == "healthy"
    assert vector_ok is True
    assert vector_details["backend"] == "qdrant"

    cache_status, cache_ok, cache_details = probes["cloud_cache"]()
    assert cache_status == "disabled"
    assert cache_ok is True
    assert cache_details["backend"] == "local"

    conn.close()
