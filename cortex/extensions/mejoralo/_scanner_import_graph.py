"""_scanner_import_graph — Import Graph analysis for the Antipattern Scanner.

Extracted from antipatterns.py to satisfy the Landauer LOC barrier (≤500).
Provides Scanner 4: Circular Deps + Fan-Out analysis.
These functions are project-wide (not per-file) — they build a full dep graph.
"""
from __future__ import annotations


import ast
import os
from pathlib import Path

from cortex.extensions.mejoralo.constants import MAX_FAN_OUT, SKIP_DIRS
from cortex.extensions.mejoralo.models import AntipatternFinding

__all__ = [
    "build_import_graph",
    "detect_circular_deps",
    "detect_fan_out",
    "run_graph_scanners",
    "MAX_FAN_OUT",
]


def _get_file_deps(fp: Path) -> set[str]:
    """Parse a file and return the set of imported root dependencies."""
    try:
        content = fp.read_text(errors="replace")
        tree = ast.parse(content)
    except (SyntaxError, OSError):
        return set()

    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                deps.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                deps.add(node.module.split(".")[0])
    return deps


def build_import_graph(root: Path) -> dict[str, set[str]]:
    """Build a module→dependencies graph from Python imports."""
    graph: dict[str, set[str]] = {}

    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith(".py"):
                continue
            fp = Path(dirpath) / f
            rel = str(fp.relative_to(root))
            module_name = rel.replace("/", ".").removesuffix(".py")
            if module_name.endswith(".__init__"):
                module_name = module_name.removesuffix(".__init__")
            graph[module_name] = _get_file_deps(fp)

    return graph


def _check_circular_dep(
    module: str,
    mod_root: str,
    dep: str,
    graph: dict[str, set[str]],
    root_to_modules: dict[str, list[str]],
    seen: set[tuple[str, str]],
    circular: list[tuple[str, str]],
) -> None:
    for other_mod in root_to_modules.get(dep, []):
        if mod_root in graph[other_mod]:
            pair = tuple(sorted((mod_root, dep)))
            if pair not in seen:
                seen.add(pair)  # type: ignore[arg-type]
                circular.append((module, other_mod))


def detect_circular_deps(graph: dict[str, set[str]]) -> list[tuple[str, str]]:
    """Find circular dependency pairs in the import graph."""
    circular: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    root_to_modules: dict[str, list[str]] = {}

    for mod in graph:
        root_to_modules.setdefault(mod.split(".")[0], []).append(mod)

    for module, deps in graph.items():
        mod_root = module.split(".")[0]
        for dep in deps:
            if dep != mod_root:
                _check_circular_dep(module, mod_root, dep, graph, root_to_modules, seen, circular)

    return circular


def detect_fan_out(
    graph: dict[str, set[str]],
    root_package: str,
) -> list[tuple[str, int]]:
    """Find modules with too many dependencies (high fan-out)."""
    violations: list[tuple[str, int]] = []
    for module, deps in graph.items():
        local_deps = {d for d in deps if d == root_package or d.startswith(f"{root_package}.")}
        if len(local_deps) > MAX_FAN_OUT:
            violations.append((module, len(local_deps)))
    return violations


def run_graph_scanners(
    scan_root: Path, root_package: str, findings: list[AntipatternFinding]
) -> None:
    """Run circular dependency and fan-out scanners on a project directory."""
    graph = build_import_graph(scan_root)

    for mod_a, mod_b in detect_circular_deps(graph):
        findings.append(
            AntipatternFinding(
                scanner="CircularDep",
                severity="high",
                file=mod_a.replace(".", "/") + ".py",
                line=0,
                message=f"Circular dependency: {mod_a} ↔ {mod_b}",
                fix_hint="Break the cycle with dependency injection or an interface module.",
            )
        )

    for module, count in detect_fan_out(graph, root_package):
        findings.append(
            AntipatternFinding(
                scanner="FanOut",
                severity="medium",
                file=module.replace(".", "/") + ".py",
                line=0,
                message=(
                    f"High fan-out: {module} depends on {count} local modules (max: {MAX_FAN_OUT})"
                ),
                fix_hint="Consider splitting this module or using a facade pattern.",
            )
        )
