import ast

from cortex.guards.models import EXEC_MODULES, SOVEREIGN_MARKERS


def has_exec_import(source: str) -> bool:
    """Check if the file imports any process execution module."""
    return any(mod in source for mod in EXEC_MODULES)


def has_sovereign_fallback(source: str) -> bool:
    """Check if the file has sovereign LLM fallback."""
    return any(m in source for m in SOVEREIGN_MARKERS)


class DiscoveryScanner:
    """Scanner for heuristic execution triggers."""

    def scan(self, node: ast.AST) -> list[tuple[int, str, str]]:
        # Heuristics are usually file-level, but we can detect imports here
        results = []
        if isinstance(node, ast.Import):
            for name in node.names:
                if name.name in EXEC_MODULES:
                    results.append((node.lineno, name.name, "execution_import"))
        elif isinstance(node, ast.ImportFrom):
            if node.module in EXEC_MODULES:
                results.append((node.lineno, str(node.module), "execution_import"))
        return results
