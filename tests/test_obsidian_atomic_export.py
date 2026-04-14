from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

from cortex.extensions.sync import obsidian


class _DummyCursor:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    async def __aenter__(self) -> _DummyCursor:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def fetchall(self) -> list[tuple]:
        return self._rows


class _DummyConn:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    async def __aenter__(self) -> _DummyConn:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str) -> _DummyCursor:
        return _DummyCursor(self._rows)


class _DummyEngine:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def session(self) -> _DummyConn:
        return _DummyConn(self._rows)


def test_export_obsidian_writes_notes_projects_tags_and_dashboard(tmp_path: Path) -> None:
    vault_path = tmp_path / "vault"
    rows = [
        (
            7,
            "demo-project",
            "Important architectural decision",
            "decision",
            '["tag-a"]',
            0.95,
            1.0,
            "2026-04-14T00:00:00Z",
            "2026-04-14T00:00:00Z",
            None,
        )
    ]

    stats = asyncio.run(obsidian.export_obsidian(_DummyEngine(rows), vault_path=vault_path))

    fact_note = vault_path / "decisions" / "decision-7.md"
    project_note = vault_path / "projects" / "demo-project.md"
    tag_note = vault_path / "tags" / "tag-a.md"
    dashboard = vault_path / "🧠 CORTEX Dashboard.md"

    assert stats["notes_created"] == 4
    assert stats["projects"] == ["demo-project"]
    assert stats["tags"] == ["tag-a"]
    assert fact_note.exists()
    assert project_note.exists()
    assert tag_note.exists()
    assert dashboard.exists()
    assert "Important architectural decision" in fact_note.read_text(encoding="utf-8")
    assert "[[projects/demo-project|demo-project]]" in dashboard.read_text(encoding="utf-8")
    project_content = project_note.read_text(encoding="utf-8")
    tag_content = tag_note.read_text(encoding="utf-8")

    assert "type: \"moc\"" in project_content
    assert 'project: "demo-project"' in project_content
    assert "# 📂 demo-project" in project_content
    assert "> 1 active facts" in project_content
    assert "- [[decisions/decision-7|#7]] — Important architectural decision" in project_content
    assert "## ⚡ Decision (1)" in project_content
    assert "type: \"tag-index\"" in tag_content
    assert 'tag: "tag-a"' in tag_content
    assert "count: 1" in tag_content
    assert "# 🏷️ tag-a" in tag_content
    assert "> 1 facts tagged with `tag-a`" in tag_content
    assert "- [[decisions/decision-7|#7]] (demo-project) — Important architectural decision" in tag_content


def test_obsidian_module_uses_atomic_write_helpers() -> None:
    source = inspect.getsource(obsidian)

    assert "atomic_write(" in source
    assert ".write_text(" not in source
