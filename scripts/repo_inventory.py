"""
Repository inventory generator.

Produces three artefacts under artifacts/:
  - stats.json    : machine-readable metrics
  - tree.txt      : git-tracked file tree snapshot
  - inventory.md  : human-readable markdown inventory

Usage:
    python scripts/repo_inventory.py
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

IGNORED_DIRS: set[str] = {
    ".git",
    ".venv",
    ".venv_transcript",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "cortex_persist.egg-info",
    "cortex_memory.egg-info",
    "*.egg-info",
}

TEXT_EXTENSIONS: set[str] = {
    ".py",
    ".md",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
    ".ini",
    ".cfg",
    ".sh",
    ".sql",
    ".rst",
}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def git_cmd(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def main() -> None:
    files = list(iter_files(ROOT))
    by_ext: Counter[str] = Counter()
    line_counts: Counter[str] = Counter()
    total_lines = 0

    for file in files:
        ext = file.suffix.lower() or "<no_ext>"
        by_ext[ext] += 1
        if ext in TEXT_EXTENSIONS:
            lines = count_lines(file)
            line_counts[ext] += lines
            total_lines += lines

    # Top-level dirs (excluding hidden and ignored)
    top_level_dirs = sorted(
        p.name
        for p in ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in IGNORED_DIRS
    )

    stats: dict = {
        "repo_name": ROOT.name,
        "git_branch": git_cmd(["rev-parse", "--abbrev-ref", "HEAD"]),
        "git_commit": git_cmd(["rev-parse", "HEAD"]),
        "git_commit_short": git_cmd(["rev-parse", "--short", "HEAD"]),
        "tracked_files": len(files),
        "text_lines": total_lines,
        "files_by_extension": dict(sorted(by_ext.items())),
        "lines_by_extension": dict(sorted(line_counts.items())),
        "top_level_directories": top_level_dirs,
    }

    # ── stats.json ────────────────────────────────────────────────────────────
    (ARTIFACTS / "stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── tree.txt ──────────────────────────────────────────────────────────────
    tree_output = git_cmd(["ls-tree", "-r", "--name-only", "HEAD"])
    (ARTIFACTS / "tree.txt").write_text(tree_output + "\n", encoding="utf-8")

    # ── inventory.md ──────────────────────────────────────────────────────────
    lines = [
        "# Repository Inventory",
        "",
        f"- **Repo**: `{stats['repo_name']}`",
        f"- **Branch**: `{stats['git_branch']}`",
        f"- **Commit**: `{stats['git_commit']}`",
        f"- **Tracked files**: {stats['tracked_files']}",
        f"- **Text lines**: {stats['text_lines']}",
        "",
        "## Top-level directories",
        "",
    ]
    lines.extend(f"- `{d}`" for d in top_level_dirs)
    lines += [
        "",
        "## Files by extension",
        "",
    ]
    for ext, count in sorted(by_ext.items()):
        lines.append(f"- `{ext}`: {count}")
    lines += [
        "",
        "## Lines by extension",
        "",
    ]
    for ext, count in sorted(line_counts.items()):
        lines.append(f"- `{ext}`: {count}")

    (ARTIFACTS / "inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"✅  Inventory written to {ARTIFACTS}")
    print(f"   tracked_files : {stats['tracked_files']}")
    print(f"   text_lines    : {stats['text_lines']}")
    print(f"   branch        : {stats['git_branch']} @ {stats['git_commit_short']}")


if __name__ == "__main__":
    main()
