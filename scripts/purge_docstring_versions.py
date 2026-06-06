#!/usr/bin/env python3
"""
Mode: C5-REAL | C4-SIM
Action: Purge docstring versions
SSOT: pyproject.toml
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".venv", ".venv-audit", "__pycache__", "node_modules", ".git", "engine-c5"}

PATTERN = re.compile(r"CORTEX\s+v[\d.]+\s*[-–\-]\s*", re.IGNORECASE)

def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)

def process_file(filepath: Path, dry_run: bool = False) -> bool:
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return False

    new_content = PATTERN.sub("", content)
    if new_content == content:
        return False

    new_content = re.sub(r'"""[\s]*"""', '""""""', new_content)
    new_content = re.sub(r'^""""""[\s]*\n', "", new_content, flags=re.MULTILINE)

    if dry_run:
        return True

    filepath.write_text(new_content, encoding="utf-8")
    return True

def main() -> None:
    dry_run = "--dry-run" in sys.argv
    reality_level = "C4-SIM" if dry_run else "C5-REAL"
    print(f"REALITY_LEVEL: {reality_level}")
    
    modified = []
    scanned = 0

    for py_file in sorted(REPO.rglob("*.py")):
        if should_skip(py_file):
            continue
        scanned += 1
        if process_file(py_file, dry_run=dry_run):
            modified.append(str(py_file.relative_to(REPO)))

    print("---")
    print("Action: DocstringPurge")
    print(f"Scanned: {scanned}")
    print(f"Modified: {len(modified)}")
    if modified:
        print("Files:")
        for f in modified:
            print(f"  - {f}")
    if not dry_run and modified:
        print("State: SSOT_ENFORCED")

if __name__ == "__main__":
    main()
