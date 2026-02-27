"""ConnectionGuard — CI/lint scanner for raw sqlite3.connect() usage.

Provides a callable scanner that detects unauthorized sqlite3.connect()
calls from CORTEX module code. Used by:
1. CI quality gates (GitHub Actions)
2. Pre-commit hooks
3. cortex lint command

This is a build-time guard, not runtime — pragmatic and zero-overhead.

Copyright 2026 Borja Moskv — Apache-2.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

__all__ = ["scan_raw_connects", "ConnectionViolation"]

# Modules allowed to use sqlite3.connect directly
_WHITELISTED_MODULES: frozenset[str] = frozenset(
    {
        "cortex/database/core.py",
        "cortex/database/pool.py",
        "cortex/database/writer.py",
        "cortex/engine/sync_compat.py",
        "cortex/database/connection_guard.py",
        "cortex/memory/sqlite_vec_store.py",  # Low-level vec extension needs raw connect
        "cortex/memory/hdc/store.py",  # HDC Specular Memory needs raw access
        "cortex/agents/system_prompt.py",  # Documentation strings, not actual usage
        "cortex/evolution/cortex_metrics.py",  # Low-level sync telemetry metrics
    }
)

# Pattern: raw sqlite3.connect( call
_RAW_CONNECT_PATTERN = re.compile(r"(?<!\w)sqlite3\.connect\s*\(", re.MULTILINE)

# Pattern: import sqlite3 (to differentiate from type hints)
_IMPORT_PATTERN = re.compile(r"^\s*import\s+sqlite3|^\s*from\s+sqlite3\s+import", re.MULTILINE)


class ConnectionViolation:
    """Represents a raw sqlite3.connect() usage violation."""

    def __init__(self, filepath: str, line_number: int, line_content: str) -> None:
        self.filepath = filepath
        self.line_number = line_number
        self.line_content = line_content.strip()

    def __str__(self) -> str:
        return f"{self.filepath}:{self.line_number}: {self.line_content}"

    def __repr__(self) -> str:
        return f"ConnectionViolation({self.filepath!r}, {self.line_number})"


def _scan_file_lines(py_file: Path, violations: list[ConnectionViolation]) -> None:
    try:
        content = py_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    for i, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(("#", '"""', "'''", '"', "'")):
            continue

        if "sqlite3.connect" in stripped:
            before = stripped.split("sqlite3.connect")[0]
            if before.count('"') % 2 == 1 or before.count("'") % 2 == 1:
                continue

        if _RAW_CONNECT_PATTERN.search(line):
            violations.append(ConnectionViolation(str(py_file), i, line))


def scan_raw_connects(
    root: str | Path = "cortex",
    whitelist: frozenset[str] | None = None,
) -> list[ConnectionViolation]:
    """Scan CORTEX source for unauthorized sqlite3.connect() calls.

    Args:
        root: Root directory to scan.
        whitelist: Override the default whitelisted module paths.

    Returns:
        List of ConnectionViolation instances.
    """
    allowed = whitelist or _WHITELISTED_MODULES
    root_path = Path(root)
    violations: list[ConnectionViolation] = []

    for py_file in root_path.rglob("*.py"):
        rel_path = str(py_file)
        if any(rel_path.endswith(w) for w in allowed):
            continue
        if "/tests/" in rel_path or rel_path.startswith("tests/"):
            continue

        _scan_file_lines(py_file, violations)

    return violations


def main() -> int:
    """CLI entry point for CI integration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan for unauthorized sqlite3.connect() usage in CORTEX"
    )
    parser.add_argument(
        "--root",
        default="cortex",
        help="Root directory to scan (default: cortex)",
    )
    args = parser.parse_args()

    violations = scan_raw_connects(args.root)

    if violations:
        print(f"\n🔴 CONNECTION GUARD: {len(violations)} violation(s) found!\n")
        print("These files use raw sqlite3.connect() instead of CortexEngine:")
        print("─" * 60)
        for v in violations:
            print(f"  ✗ {v}")
        print("─" * 60)
        print("\nFix: Use CortexEngine.get_conn() or database.core.connect()")
        print("If this module genuinely needs raw access, add it to the whitelist")
        print(f"in {__file__}")
        return 1

    print("✅ CONNECTION GUARD: No unauthorized sqlite3.connect() usage found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
