#!/usr/bin/env python3
"""Lightweight repo-health checks for changed files.

This guard is intentionally dependency-free so it can run early in CI.
It focuses on high-signal failures that should never land in new changes:

- unresolved merge conflict markers
- Python syntax errors

By default it inspects files changed in the current Git diff context.
You can also pass file paths explicitly, or use ``--all`` to scan the repo.
"""

from __future__ import annotations

import argparse
import py_compile
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _changed_files import changed_files, paths_from_output, run_git, unique_paths, untracked_files

CONFLICT_MARKERS = ("<" * 7 + " ", ">" * 7 + " ")
CONFLICT_SEPARATOR = "=" * 7


def _changed_files_from_git(*, include_untracked: bool = False) -> list[Path]:
    paths, _ = changed_files(include_untracked=include_untracked, prefer_staged=False)
    return paths


def _all_repo_files() -> list[Path]:
    tracked = paths_from_output(run_git(["ls-files"]))
    return unique_paths(tracked, untracked_files())


def _text_contains_conflict_markers(path: Path) -> list[int]:
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    bad_lines: list[int] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        if line.startswith(CONFLICT_MARKERS) or line == CONFLICT_SEPARATOR:
            bad_lines.append(line_no)
    return bad_lines


def _check_python_syntax(path: Path) -> str | None:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as err:
        return str(err)
    return None


def _collect_targets(args: argparse.Namespace) -> list[Path]:
    if args.files:
        files = [Path(item) for item in args.files]
    elif args.all:
        files = _all_repo_files()
    else:
        files = _changed_files_from_git(include_untracked=args.include_untracked)
    return [path for path in files if path.exists() and path.is_file()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run lightweight repo-health checks.")
    parser.add_argument("files", nargs="*", help="Optional explicit files to inspect.")
    parser.add_argument("--all", action="store_true", help="Scan all tracked and untracked files.")
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Include untracked files in the default changed-files scan.",
    )
    args = parser.parse_args()

    try:
        targets = _collect_targets(args)
    except subprocess.CalledProcessError as err:
        print(f"[repo-health] git command failed: {err}", file=sys.stderr)
        return 2

    if not targets:
        print("[repo-health] No files to inspect.")
        return 0

    failures: list[str] = []

    for path in targets:
        marker_lines = _text_contains_conflict_markers(path)
        if marker_lines:
            joined = ", ".join(str(line) for line in marker_lines[:10])
            failures.append(f"{path}: merge conflict markers at lines {joined}")

        if path.suffix == ".py":
            syntax_error = _check_python_syntax(path)
            if syntax_error:
                failures.append(f"{path}: syntax error\n{syntax_error}")

    if failures:
        print("[repo-health] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"[repo-health] OK ({len(targets)} files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
