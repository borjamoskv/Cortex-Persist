# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "repo_health_changed.py"
    spec = importlib.util.spec_from_file_location("repo_health_changed", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_changed_files_local_fallback_uses_unstaged_when_index_is_empty(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "changed_files",
        lambda *, include_untracked, prefer_staged: (
            [Path("cortex/api/core.py"), Path("README.md")],
            "combined",
        ),
    )

    assert module._changed_files_from_git() == [
        Path("cortex/api/core.py"),
        Path("README.md"),
    ]


def test_changed_files_can_merge_untracked_without_duplicates(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        module,
        "changed_files",
        lambda *, include_untracked, prefer_staged: (
            [
                Path("cortex/api/core.py"),
                Path("tests/test_repo_health_changed.py"),
                Path("scripts/repo_health_changed.py"),
            ],
            "combined",
        ),
    )

    assert module._changed_files_from_git(include_untracked=True) == [
        Path("cortex/api/core.py"),
        Path("tests/test_repo_health_changed.py"),
        Path("scripts/repo_health_changed.py"),
    ]
