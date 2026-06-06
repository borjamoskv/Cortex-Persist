# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(name: str):
    script_path = REPO_ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_entropy_gate_falls_back_to_local_python_diff(monkeypatch, tmp_path):
    fake_radon = types.ModuleType("radon")
    fake_complexity = types.ModuleType("radon.complexity")
    fake_complexity.cc_visit = lambda code: []
    fake_radon.complexity = fake_complexity
    monkeypatch.setitem(sys.modules, "radon", fake_radon)
    monkeypatch.setitem(sys.modules, "radon.complexity", fake_complexity)

    module = _load_script_module("entropy_gate.py")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tracked.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    (tmp_path / "scratch.py").write_text("def also_ok():\n    return 2\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# ignored\n", encoding="utf-8")

    monkeypatch.setattr(
        module,
        "changed_files",
        lambda *, include_untracked, prefer_staged: (
            [Path("tracked.py"), Path("notes.md"), Path("scratch.py")],
            "worktree",
        ),
    )

    files, source = module.get_candidate_python_files()

    assert source == "worktree"
    assert files == [tmp_path / "tracked.py", tmp_path / "scratch.py"]


def test_sovereign_pre_commit_reads_untracked_file_contents_when_no_diff(monkeypatch, tmp_path):
    module = _load_script_module("sovereign_pre_commit.py")
    secret_key = "wallet" + "_seed"
    secret_file = tmp_path / f"{secret_key}.txt"
    secret_file.write_text(f"{secret_key}=ultra-secret\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "run_git", lambda args, check=False: "")

    violations = module.check_file_contents(
        [str(secret_file)],
        source="worktree",
        untracked_files={str(secret_file)},
    )

    assert violations == [
        f"- CONTENT: {secret_file} | {module.CONTENT_PATTERNS[0].pattern}"
    ]

