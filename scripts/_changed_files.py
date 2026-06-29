#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
cat_id: -changed-files
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


from __future__ import annotations

import os
import subprocess
from pathlib import Path


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
    """Resolve changed files from the current Git context.

    In CI, compare against the upstream/base revision. Locally, either return the
    staged slice first or the union of staged and unstaged files, depending on
    ``prefer_staged``.
    """

    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        merge_base = f"origin/{base_ref}...HEAD"
        paths = paths_from_output(
            run_git(["diff", "--name-only", "--diff-filter=ACMR", merge_base])
        )
        if include_untracked:
            paths = unique_paths(paths, untracked_files())
        return paths, "ci"

    before = os.environ.get("GITHUB_EVENT_BEFORE")
    if before and before != "0000000000000000000000000000000000000000":
        paths = paths_from_output(
            run_git(["diff", "--name-only", "--diff-filter=ACMR", before, "HEAD"])
        )
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
