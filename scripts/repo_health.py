#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""Lightweight repo-health checks for changed files and git utilities."""

from __future__ import annotations

import argparse
import os
import py_compile
import subprocess
import sys
from pathlib import Path

# --- GIT UTILITIES ---

def run_git(args: list[str], *, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()

def paths_from_output(output: str) -> list[Path]:
    return [Path(line) for line in output.splitlines() if line]

def unique_paths(*groups: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for group in groups:
        for path in group:
            if path in seen:
                continue
            seen.add(path)
            ordered.append(path)
    return ordered

def untracked_files() -> list[Path]:
    return paths_from_output(run_git(["ls-files", "--others", "--exclude-standard"]))

def changed_files(
    *,
    include_untracked: bool = False,
    prefer_staged: bool = False,
) -> tuple[list[Path], str]:
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        merge_base = f"origin/{base_ref}...HEAD"
        paths = paths_from_output(run_git(["diff", "--name-only", "--diff-filter=ACMR", merge_base]))
        if include_untracked:
            paths = unique_paths(paths, untracked_files())
        return paths, "ci"

    before = os.environ.get("GITHUB_EVENT_BEFORE")
    if before and before != "0000000000000000000000000000000000000000":
        paths = paths_from_output(run_git(["diff", "--name-only", "--diff-filter=ACMR", before, "HEAD"]))
        if include_untracked:
            paths = unique_paths(paths, untracked_files())
        return paths, "ci"

    unstaged = paths_from_output(run_git(["diff", "--name-only", "--diff-filter=ACMR"]))
    staged = paths_from_output(run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"]))

    if prefer_staged and staged:
        paths = staged
        source = "staged"
    elif prefer_staged:
        paths = unstaged
        source = "worktree"
    else:
        paths = unique_paths(unstaged, staged)
        source = "combined"

    if include_untracked and (not prefer_staged or source != "staged"):
        paths = unique_paths(paths, untracked_files())

    if not paths and prefer_staged:
        return [], "worktree"
    return paths, source

# --- HEALTH CHECKS ---

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
