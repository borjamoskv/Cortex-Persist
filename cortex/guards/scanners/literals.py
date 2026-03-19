import ast
from pathlib import Path

from cortex.guards.models import ORACLE_BINARIES


def oracle_in_str(value: str) -> str | None:
    """Return oracle name if found in string, else None."""
    lower = value.lower()
    for oracle in ORACLE_BINARIES:
        if oracle in lower:
            return oracle
    return None


def scan_args_for_oracles(node: ast.Call) -> list[str]:
    """Scan positional AND keyword args for oracle references."""
    found: list[str] = []
    all_args = list(node.args) + [kw.value for kw in node.keywords]

    for arg in all_args:
        if isinstance(arg, ast.List):
            found.extend(scan_list(arg))
        elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            hit = oracle_in_str(arg.value)
            if hit:
                found.append(hit)
        elif isinstance(arg, ast.JoinedStr):
            found.extend(scan_fstring(arg))
        elif isinstance(arg, ast.Name):
            found.extend(scan_variable_name(arg))
    return found


def scan_list(node: ast.List) -> list[str]:
    """Scan list literal elements for oracle references."""
    found: list[str] = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            name = Path(elt.value).name.lower()
            if name in ORACLE_BINARIES:
                found.append(name)
        elif isinstance(elt, ast.Name):
            found.extend(scan_variable_name(elt))
    return found


def scan_fstring(node: ast.JoinedStr) -> list[str]:
    """Scan f-string for oracle references in constant parts."""
    found: list[str] = []
    for val in node.values:
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            hit = oracle_in_str(val.value)
            if hit:
                found.append(hit)
    return found


def scan_variable_name(node: ast.Name) -> list[str]:
    """Check if a variable name references an oracle."""
    lower = node.id.lower()
    return [node.id for o in ORACLE_BINARIES if o in lower]


class LiteralsScanner:
    """Scanner for oracle references in string literals and variables."""

    def scan(self, node: ast.AST) -> list[tuple[int, str, str]]:
        results = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            hit = oracle_in_str(node.value)
            if hit:
                results.append((getattr(node, "lineno", 0), hit, "string_literal"))
        return results
