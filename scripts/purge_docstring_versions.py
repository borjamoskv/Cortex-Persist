#!/usr/bin/env python3
"""Purge decorative 'CORTEX vX.Y - ' prefixes from module docstrings.

Single source of truth for version = pyproject.toml (0.3.0b7).
SCHEMA_VERSION (5.4.3) is independent and stays in database/schema.py.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".venv", ".venv-audit", "__pycache__", "node_modules", ".git", "engine-c5"}

# Pattern: "CORTEX vX.Y.Z - " or "CORTEX vX.Y - " or "CORTEX vX - "
# Handles both em-dash (-) and en-dash (–) and hyphen (-)
PATTERN = re.compile(
    r"CORTEX\s+v[\d.]+\s*[-–\-]\s*",
    re.IGNORECASE,
)


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def process_file(filepath: Path, dry_run: bool = False) -> bool:
    """Return True if file was modified."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return False

    new_content = PATTERN.sub("", content)

    if new_content == content:
        return False

    # Clean up empty docstrings that result from purge (e.g., '"""\n"""')
    # Handle case where entire docstring was just the version tag
    new_content = re.sub(r'"""[\s]*"""', '""""""', new_content)
    # Remove fully empty module docstrings
    new_content = re.sub(r'^""""""[\s]*\n', "", new_content, flags=re.MULTILINE)

    if dry_run:
        return True

    filepath.write_text(new_content, encoding="utf-8")
    return True


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    mode = "DRY-RUN" if dry_run else "LIVE"
    print(f"[{mode}] Purging decorative CORTEX version tags...")

    modified = []
    scanned = 0

    for py_file in sorted(REPO.rglob("*.py")):
        if should_skip(py_file):
            continue
        scanned += 1
        if process_file(py_file, dry_run=dry_run):
            modified.append(py_file.relative_to(REPO))

    print(f"\nScanned: {scanned}")
    print(f"Modified: {len(modified)}")

    if modified:
        print("\nFiles changed:")
        for f in modified:
            print(f"  {f}")

    if not dry_run and modified:
        print(f"\n✅ {len(modified)} files purged. SSOT = pyproject.toml (0.3.0b7)")


if __name__ == "__main__":
    main()
