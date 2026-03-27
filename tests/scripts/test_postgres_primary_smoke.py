from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, relative_path: str):
    module_path = _REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exercise_api_client_reports_full_postgres_vertical() -> None:
    smoke = _load_module("postgres_primary_smoke", "scripts/postgres_primary_smoke.py")
    api_path_test = _load_module("test_api_postgres_primary_path", "tests/test_api_postgres_primary_path.py")
    client = api_path_test._build_client(
        embedder=api_path_test._FakeEmbedder(
            {
                "PostgreSQL smoke proof through the public API path": [1.0, 0.0, 0.0],
                "smoke proof public API": [1.0, 0.0, 0.0],
            }
        )
    )

    report = smoke.exercise_api_client(
        client,
        project="pg-smoke-test",
        content="PostgreSQL smoke proof through the public API path",
        query="smoke proof public API",
    )

    assert report["passed"] is True
    assert report["store"]["payload"]["id"] == 1
    assert report["search"]["payload"][0]["fact_id"] == 1
    assert report["vote"]["payload"]["vote"] == 1
    assert report["checkpoint"]["payload"]["checkpoint_id"] == 1
    assert report["checkpoint"]["payload"]["vote_checkpoint_id"] == 1
    assert report["ledger"]["payload"]["valid"] is True
