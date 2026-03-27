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


def test_build_markdown_report_summarizes_smoke_output() -> None:
    evidence = _load_module("postgres_primary_evidence", "scripts/postgres_primary_evidence.py")
    report = {
        "timestamp": "2026-03-27T10:00:00+00:00",
        "target": "postgresql://smoke@127.0.0.1:55432/cortex_smoke",
        "tenant_id": "tenant-pg-smoke-1234",
        "project": "pg-smoke-1234",
        "passed": True,
        "store": {"payload": {"id": 7}},
        "search": {"payload": [{"fact_id": 7}]},
        "vote": {"payload": {"vote": 1}},
        "checkpoint": {"payload": {"checkpoint_id": 2, "vote_checkpoint_id": 3}},
        "ledger": {
            "payload": {
                "valid": True,
                "tx_checked": 5,
                "roots_checked": 1,
                "votes_checked": 1,
                "vote_checkpoints_checked": 1,
                "violations": [],
            }
        },
    }

    markdown = evidence.build_markdown_report(report)

    assert "# PostgreSQL Vertical Smoke Evidence" in markdown
    assert "`PASS`" in markdown
    assert "Stored fact id: `7`" in markdown
    assert "Transaction checkpoint id: `2`" in markdown
    assert "Vote checkpoint id: `3`" in markdown
    assert "Ledger valid: `True`" in markdown
