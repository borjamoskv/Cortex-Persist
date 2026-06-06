# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "_changed_files.py"
    spec = importlib.util.spec_from_file_location("_changed_files", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_changed_files_prefers_staged_when_requested(monkeypatch):
    module = _load_module()

    def fake_run_git(args, *, check=True):
        outputs = {
            ("diff", "--name-only", "--diff-filter=ACMR"): "worktree_only.py\n",
            ("diff", "--cached", "--name-only", "--diff-filter=ACMR"): "staged_only.py\n",
            ("ls-files", "--others", "--exclude-standard"): "scratch.py\n",
        }
        return outputs[tuple(args)]

    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_BEFORE", raising=False)
    monkeypatch.setattr(module, "run_git", fake_run_git)

    files, source = module.changed_files(include_untracked=True, prefer_staged=True)

    assert source == "staged"
    assert files == [Path("staged_only.py")]


def test_changed_files_combines_local_diff_for_repo_health(monkeypatch):
    module = _load_module()

    def fake_run_git(args, *, check=True):
        outputs = {
            ("diff", "--name-only", "--diff-filter=ACMR"): "worktree_only.py\n",
            ("diff", "--cached", "--name-only", "--diff-filter=ACMR"): "staged_only.py\n",
            ("ls-files", "--others", "--exclude-standard"): "",
        }
        return outputs[tuple(args)]

    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_BEFORE", raising=False)
    monkeypatch.setattr(module, "run_git", fake_run_git)

    files, source = module.changed_files(include_untracked=False, prefer_staged=False)

    assert source == "combined"
    assert files == [Path("worktree_only.py"), Path("staged_only.py")]
