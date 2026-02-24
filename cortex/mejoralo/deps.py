"""CORTEX v5.0 — Dependency Extractor.

Calculates topological dependencies for topological sorting.
"""

import ast
import logging
from pathlib import Path

logger = logging.getLogger("cortex.mejoralo.deps")


def sort_by_topological_order(
    file_issues: dict[str, list[str]], root_path: str | Path
) -> list[tuple[str, list[str]]]:
    """Sort target files by dependency (bottom-up)."""
    import networkx as nx

    G = nx.DiGraph()
    files = set(file_issues.keys())
    root = Path(root_path).resolve()

    for rel_path in files:
        G.add_node(rel_path)
        deps = _extract_file_dependencies(root / rel_path, files)
        for d in deps:
            G.add_edge(rel_path, d)

    try:
        order = list(reversed(list(nx.topological_sort(G))))
    except nx.NetworkXUnfeasible:
        logger.warning("Circular dependencies detected. Falling back to heuristic.")
        return sorted(file_issues.items(), key=lambda x: len(x[1]), reverse=True)

    return [(f, file_issues[f]) for f in order if f in file_issues]


def _extract_file_dependencies(file_path: Path, targets: set[str]) -> set[str]:
    """Extract which target files the given file depends on."""
    if not file_path.exists() or file_path.suffix != ".py":
        return set()

    deps = set()
    try:
        tree = ast.parse(file_path.read_text(errors="replace"))
        for node in ast.walk(tree):
            mod = _get_module_name_from_node(node)
            if mod:
                _match_module_to_targets(mod, targets, deps)
    except Exception:
        pass
    return deps


def _get_module_name_from_node(node: ast.AST) -> str | None:
    """Helper to extract module true name from AST import node."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            return alias.name
    elif isinstance(node, ast.ImportFrom):
        return node.module
    return None


def _match_module_to_targets(mod: str, targets: set[str], deps: set[str]) -> None:
    """Matches an extracted module against targets and registers dependency."""
    mod_path = mod.replace(".", "/")
    for t in targets:
        if t.startswith(mod_path):
            deps.add(t)
