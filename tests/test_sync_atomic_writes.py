import asyncio
import json
from pathlib import Path

import cortex.extensions.sync.common as sync_common
import cortex.extensions.sync.gitops as sync_gitops
import cortex.extensions.sync.snapshot as sync_snapshot


def test_save_sync_state_writes_json_file(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "sync_state.json"
    monkeypatch.setattr(sync_common, "runtime_sync_state_file", lambda: target)

    sync_common.save_sync_state({"alpha": 1})

    assert json.loads(target.read_text(encoding="utf-8")) == {"alpha": 1}


def test_sync_fact_to_repo_writes_json_and_snapshot(monkeypatch, tmp_path: Path) -> None:
    repo_path = tmp_path / "demo-repo"
    repo_path.mkdir()
    monkeypatch.setattr(sync_gitops, "_locate_repo_root", lambda project: repo_path)

    ok = asyncio.run(
        sync_gitops.sync_fact_to_repo(
            "demo",
            7,
            {
                "id": 7,
                "content": "Fact content",
                "fact_type": "knowledge",
                "created_at": "2026-04-14T00:00:00Z",
                "confidence": "C4",
                "tags": ["tag-a"],
            },
        )
    )

    assert ok is True
    knowledge = json.loads((repo_path / ".cortex" / "knowledge.json").read_text(encoding="utf-8"))
    assert knowledge["facts"][0]["id"] == 7
    snapshot = (repo_path / ".cortex" / "context-snapshot.md").read_text(encoding="utf-8")
    assert "Fact content" in snapshot


def test_export_snapshot_writes_markdown_file(monkeypatch, tmp_path: Path) -> None:
    class _DummyCursor:
        def __init__(self) -> None:
            self._done = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def fetchmany(self, size: int):
            if self._done:
                return []
            self._done = True
            return [("demo", "Snapshot fact", "knowledge", '["tag-a"]', 0.9)]

    class _DummyConn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def execute(self, query, params):
            return _DummyCursor()

    class _DummyEngine:
        _db_path = tmp_path / "cortex.db"

        def session(self):
            return _DummyConn()

        async def stats(self):
            return {
                "active_facts": 1,
                "projects": ["demo"],
                "types": {"knowledge": 1},
            }

    _DummyEngine._db_path.write_text("", encoding="utf-8")
    async def _no_tips(engine):
        return []

    monkeypatch.setattr(sync_snapshot, "_generate_tips_section", _no_tips)

    out_path = asyncio.run(sync_snapshot.export_snapshot(_DummyEngine(), out_path=tmp_path / "snapshot.md"))

    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "demo" in content
    assert "**Knowledge**: 1 facts" in content
