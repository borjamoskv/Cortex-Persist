from __future__ import annotations

import asyncio
import inspect
import json
import re
from pathlib import Path

from cortex.extensions.axioms import generate_docs as generate_docs_module
from cortex.api import openapi as openapi_module
from cortex.engine import auth as auth_module
from cortex.engine.apotheosis_audits_mixin import ApotheosisAuditsMixin
from cortex.engine.reporter import ManifoldStatus, SovereignReporter
from cortex.engine.snapshots import _write_snapshot_meta
from cortex.extensions.evolution import persistence as evolution_persistence
from cortex.extensions.evolution import telemetry as evolution_telemetry


def test_export_openapi_spec_writes_json_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        openapi_module,
        "get_openapi_spec",
        lambda: {"paths": {"/health": {"get": {}}}, "components": {"schemas": {"Health": {}}}},
    )

    out_path = openapi_module.export_openapi_spec(tmp_path / "docs" / "openapi.json")

    assert out_path.exists()
    assert json.loads(out_path.read_text(encoding="utf-8"))["paths"]["/health"]["get"] == {}


def test_snapshot_meta_write_persists_json(tmp_path: Path) -> None:
    meta_path = tmp_path / "snapshots" / "snap.json"
    payload = {"name": "demo", "tx_id": 7}

    _write_snapshot_meta(meta_path, payload)

    assert json.loads(meta_path.read_text(encoding="utf-8")) == payload


def test_byzantine_auth_writes_and_consumes_challenge(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(auth_module, "AUTH_DIR", tmp_path)
    captured: dict[str, object] = {}

    async def _fast_sleep(_: float) -> None:
        challenge_path = next(tmp_path.glob("*.json"))
        challenge = json.loads(challenge_path.read_text(encoding="utf-8"))
        captured["payload"] = dict(challenge)
        challenge["status"] = "APPROVED"
        challenge_path.write_text(json.dumps(challenge), encoding="utf-8")

    monkeypatch.setattr(auth_module.asyncio, "sleep", _fast_sleep)

    approved = asyncio.run(
        auth_module.ByzantineAuthLayer.acquire_lock(
            "OS_COMMAND",
            {"command": "rm -rf /tmp/demo"},
            zenith_score=0.0,
        )
    )

    assert approved is True
    assert captured["payload"]["status"] == "PENDING"
    assert captured["payload"]["intent"] == "OS_COMMAND"


def test_sync_notebooklm_writes_digest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    class _NotebookLM:
        async def generate_digest(self) -> str:
            return "# Digest\n\nTelemetry"

        def sync_to_cloud(self, path: Path) -> str:
            return str(path)

    class _DummyAudits(ApotheosisAuditsMixin):
        def __init__(self) -> None:
            self._notebooklm = _NotebookLM()

    asyncio.run(_DummyAudits()._sync_notebooklm())

    digest_path = tmp_path / "notebooklm_sources" / "master_digest.md"
    assert digest_path.exists()
    assert "Telemetry" in digest_path.read_text(encoding="utf-8")


def test_reporter_export_json_writes_output(tmp_path: Path) -> None:
    reporter = SovereignReporter(":memory:")

    async def _collect_metrics() -> ManifoldStatus:
        return ManifoldStatus(
            timestamp="2026-04-14T00:00:00Z",
            project="demo",
            causality={"total_edges": 1},
            efficiency={"latest_roi": {}, "history_count": 0},
            signals={"total": 2},
            architecture_integrity=99.0,
            active_ghosts=0,
            db_size_mb=0.1,
            total_facts=3,
        )

    reporter.collect_metrics = _collect_metrics  # type: ignore[method-assign]
    out_path = tmp_path / "docs" / "manifold_status.json"

    asyncio.run(reporter.export_json(str(out_path)))

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["project"] == "demo"
    assert payload["signals"]["total"] == 2


def test_runtime_modules_no_direct_write_text_remain() -> None:
    assert ".write_text(" not in inspect.getsource(openapi_module)
    assert ".write_text(" not in inspect.getsource(auth_module)


def test_runtime_modules_use_atomic_patterns_for_mutations() -> None:
    checked = [
        inspect.getsource(evolution_persistence),
        inspect.getsource(evolution_telemetry),
        inspect.getsource(generate_docs_module),
    ]

    for source in checked:
        assert ".write_text(" not in source
        assert not re.search(r"\bopen\([^\n]*,\s*['\"]w['\"]", source)
