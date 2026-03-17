#!/usr/bin/env python3
"""Runtime-aware circular dependency audit for CORTEX.

Distinguishes between:
  - Top-level imports (true runtime dependencies)
  - TYPE_CHECKING-guarded imports (type-only — no runtime cycle)
  - Function-level imports (lazy/deferred — no runtime cycle)

Only reports TRUE RUNTIME circular dependencies.

Usage:
    python scripts/coupling_audit.py [--all]

    --all  : report all cycles including TYPE_CHECKING and lazy (false positives)
"""

from __future__ import annotations

import ast
import os
import sys


def classify_imports(filepath: str) -> tuple[set[str], set[str], set[str]]:
    """Classify imports into runtime, type-only, and lazy categories."""
    try:
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception:
        return set(), set(), set()

    runtime: set[str] = set()
    type_only: set[str] = set()
    lazy: set[str] = set()

    # Find TYPE_CHECKING blocks
    type_checking_ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            if (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
                isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
            ):
                end_line = max(
                    getattr(n, "end_lineno", getattr(n, "lineno", 0))
                    for n in ast.walk(node)
                )
                type_checking_ranges.append((node.lineno, end_line))

    def in_type_checking(lineno: int) -> bool:
        return any(start <= lineno <= end for start, end in type_checking_ranges)

    def in_function(node: ast.AST) -> bool:
        """Check if node is nested inside a function/method body."""
        # Walk parents — since ast doesn't track parents, we check structure
        return False  # Will use visitor pattern instead

    class ImportClassifier(ast.NodeVisitor):
        def __init__(self) -> None:
            self._in_function_depth = 0

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._in_function_depth += 1
            self.generic_visit(node)
            self._in_function_depth -= 1

        visit_AsyncFunctionDef = visit_FunctionDef

        def _classify(self, module: str, lineno: int) -> None:
            if not module or not module.startswith("cortex"):
                return
            if in_type_checking(lineno):
                type_only.add(module)
            elif self._in_function_depth > 0:
                lazy.add(module)
            else:
                runtime.add(module)

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                self._classify(alias.name, node.lineno)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.module:
                self._classify(node.module, node.lineno)

    ImportClassifier().visit(tree)
    return runtime, type_only, lazy


def main() -> None:
    show_all = "--all" in sys.argv

    base_dir = os.path.join(os.path.dirname(__file__), "..", "cortex")
    base_dir = os.path.abspath(base_dir)

    modules: dict[str, tuple[set[str], set[str], set[str]]] = {}

    for root, _, files in os.walk(base_dir):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(root, filename)
            mod_path = "cortex" + filepath[len(base_dir) :].replace("/", ".").replace(".py", "")
            if mod_path.endswith(".__init__"):
                mod_path = mod_path[:-9]
            modules[mod_path] = classify_imports(filepath)

    # Find runtime cycles
    runtime_cycles: list[tuple[str, str]] = []
    type_only_cycles: list[tuple[str, str]] = []
    lazy_cycles: list[tuple[str, str]] = []
    seen: set[frozenset[str]] = set()

    for m1, (rt1, tc1, lz1) in modules.items():
        all_imports_1 = rt1 | tc1 | lz1
        for m2 in all_imports_1:
            if m2 not in modules or m2 == m1:
                continue
            pair = frozenset({m1, m2})
            if pair in seen:
                continue

            rt2, tc2, lz2 = modules[m2]
            all_imports_2 = rt2 | tc2 | lz2

            if m1 not in all_imports_2:
                continue

            seen.add(pair)

            # Classify: cycle is "runtime" only if BOTH directions are runtime
            m1_to_m2_runtime = m2 in rt1
            m2_to_m1_runtime = m1 in rt2

            if m1_to_m2_runtime and m2_to_m1_runtime:
                runtime_cycles.append((m1, m2))
            elif m2 in (tc1 | lz1) or m1 in (tc2 | lz2):
                if m2 in tc1 or m1 in tc2:
                    type_only_cycles.append((m1, m2))
                else:
                    lazy_cycles.append((m1, m2))

    # Report
    print("=" * 70)
    print("CORTEX Coupling Audit — Runtime-Aware Analysis")
    print("=" * 70)
    print()

    if runtime_cycles:
        print(f"🔴 TRUE RUNTIME CYCLES: {len(runtime_cycles)}")
        for a, b in sorted(runtime_cycles):
            print(f"   {a} ↔ {b}")
        print()
    else:
        print("✅ No true runtime circular dependencies found.")
        print()

    if show_all:
        if type_only_cycles:
            print(f"🟡 TYPE_CHECKING cycles (safe): {len(type_only_cycles)}")
            for a, b in sorted(type_only_cycles):
                print(f"   {a} ↔ {b}")
            print()

        if lazy_cycles:
            print(f"🔵 Lazy/deferred cycles (safe): {len(lazy_cycles)}")
            for a, b in sorted(lazy_cycles):
                print(f"   {a} ↔ {b}")
            print()

    total = len(runtime_cycles) + len(type_only_cycles) + len(lazy_cycles)
    print(f"Total pairs: {total} (runtime: {len(runtime_cycles)}, "
          f"type-only: {len(type_only_cycles)}, lazy: {len(lazy_cycles)})")

    sys.exit(1 if runtime_cycles else 0)


if __name__ == "__main__":
    main()
