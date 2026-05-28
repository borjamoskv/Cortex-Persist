#!/usr/bin/env python3
"""Merge conflict purge — keep HEAD (sovereign-security-hardening-v6).

Strategy: HEAD version includes tenant_id params, removed Optional (UP007),
and all 10-Seals security hardening. origin/main is the older baseline.
We keep HEAD blocks and discard incoming (origin/main) blocks.
"""

import re
import sys
from pathlib import Path

CONFLICT_RE = re.compile(
    r'^<<<<<<< HEAD\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]+\n',
    re.MULTILINE | re.DOTALL,
)


def resolve_file(path: Path, dry_run: bool = False) -> int:
    """Resolve all conflicts in a file by keeping HEAD. Returns count resolved."""
    content = path.read_text(encoding="utf-8", errors="replace")
    resolved, count = CONFLICT_RE.subn(r'\1', content)
    if count > 0 and not dry_run:
        path.write_text(resolved, encoding="utf-8")
    return count


def main():
    dry_run = "--dry-run" in sys.argv
    root = Path("cortex")
    files = sorted(root.rglob("*.py"))

    total_conflicts = 0
    total_files = 0

    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "<<<<<<< HEAD" not in content:
            continue
        count = resolve_file(f, dry_run=dry_run)
        if count > 0:
            total_files += 1
            total_conflicts += count
            prefix = "[DRY] " if dry_run else "[FIX] "
            print(f"{prefix}{f} — {count} conflicts")

    print(f"\n{'DRY RUN' if dry_run else 'RESOLVED'}: {total_conflicts} conflicts in {total_files} files")


if __name__ == "__main__":
    main()
