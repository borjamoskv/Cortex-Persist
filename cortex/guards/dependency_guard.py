# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""CORTEX v5.0 — DependencyGuard v2: Axiom 4 Enforcement.

Red-Teamed static analysis guard. Detects oracle dependencies through
MULTIPLE detection strategies, not just subprocess pattern matching.
"""

from __future__ import annotations

import ast
import logging
import sys
from pathlib import Path

from cortex.guards.models import DependencyViolation
from cortex.guards import analysis

__all__ = ["DependencyViolation", "scan_file", "scan_directory"]

logger = logging.getLogger("cortex.guards.dependency_guard")


def scan_file(filepath: str | Path) -> list[DependencyViolation]:
    """Scan a single Python file for Axiom 4 violations."""
    filepath = Path(filepath)
    if not filepath.exists() or filepath.suffix != ".py":
        return []

    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    # Quick exit: no exec-capable imports → no risk
    if not analysis.has_exec_import(source):
        return []

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    has_fallback = analysis.has_sovereign_fallback(source)

    # Skip self-detection
    if filepath.name in ("dependency_guard.py", "analysis.py", "models.py"):
        return []

    # Run all detection layers
    exec_calls = analysis.has_exec_calls(tree)
    hits = analysis.find_violations(tree)
    hits.extend(
        analysis.find_oracle_string_literals(tree, exec_calls)
    )

    # Deduplicate by (line, binary)
    seen: set[tuple[int, str]] = set()
    violations: list[DependencyViolation] = []
    for line, binary, call_type in hits:
        key = (line, binary)
        if key in seen:
            continue
        seen.add(key)
        
        is_heuristic = call_type == "string_literal"
        violations.append(
            DependencyViolation(
                file=str(filepath),
                line=line,
                binary=binary,
                call_type=call_type,
                has_fallback=True if is_heuristic else has_fallback,
            )
        )

    return violations


def scan_directory(
    directory: str | Path,
    *,
    exclude_venv: bool = True,
    exclude_tests: bool = False,
) -> list[DependencyViolation]:
    """Recursively scan a directory for Axiom 4 violations."""
    directory = Path(directory)
    violations: list[DependencyViolation] = []

    exclude_dirs = {"__pycache__", ".git", "node_modules"}
    if exclude_venv:
        exclude_dirs |= {".venv", "venv", "env", ".env"}
    if exclude_tests:
        exclude_dirs.add("tests")

    for py_file in directory.rglob("*.py"):
        if any(excl in py_file.parts for excl in exclude_dirs):
            continue
        violations.extend(scan_file(py_file))

    return violations


def main() -> None:
    """CLI entry point for DependencyGuard."""
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    target_path = Path(target).expanduser().resolve()

    print(
        "🛡️  DependencyGuard v2 — Axiom 4 Enforcement\n"
        f"   Scanning: {target_path}\n"
    )

    violations = scan_file(target_path) if target_path.is_file() else scan_directory(target_path)

    if not violations:
        print("✅ No Axiom 4 violations detected. Sovereignty intact.")
        return

    critical = sum(1 for v in violations if not v.has_fallback)
    warnings = len(violations) - critical

    for v in violations:
        print(f"   {v}")

    print(f"\n{'🔴' if critical else '🟡'} Total: {len(violations)} violations ({critical} CRITICAL, {warnings} warnings)")

    if critical > 0:
        print("\n⚠️  CRITICAL violations detected. Use SovereignLLM (cortex/llm/sovereign.py) to replace subprocess oracle calls.")
        sys.exit(1)


if __name__ == "__main__":
    main()
