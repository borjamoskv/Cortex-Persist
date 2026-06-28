# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import ast
import logging
import unicodedata

logger = logging.getLogger("cortex.guards.homoglyph_guard")


class SecurityViolation(Exception):
    """Raised when a security violation (e.g. homoglyph attack) is detected in the AST."""

    pass


class AntiHomoglyphVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.homoglyphs_found: list[tuple[str, str, str, int]] = []

    def check_name(self, name: str, node: ast.AST) -> None:
        for char in name:
            category = unicodedata.category(char)
            if ord(char) > 127 or category not in {"Ll", "Lu", "Nd", "Pc"}:
                try:
                    char_name = unicodedata.name(char)
                except ValueError:
                    char_name = "UNKNOWN"
                self.homoglyphs_found.append((name, char, char_name, getattr(node, "lineno", 0)))

    def visit_Name(self, node: ast.Name) -> None:
        self.check_name(node.id, node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.check_name(node.name, node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.check_name(node.name, node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.check_name(node.name, node)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self.check_name(node.arg, node)
        self.generic_visit(node)


def cassandra_validate_identifiers(tree: ast.AST) -> None:
    """
    Walks the AST tree and validates all identifiers.
    Rejects any identifier (Name, FunctionDef, AsyncFunctionDef, ClassDef, arg)
    containing ord(ch) > 127 or Unicode category outside {Ll, Lu, Nd, Pc}.
    Raises SecurityViolation on detection.
    """
    visitor = AntiHomoglyphVisitor()
    visitor.visit(tree)
    if visitor.homoglyphs_found:
        msg = ", ".join(
            [
                f"'{name}' contains '{char}' ({char_name}) at line {line}"
                for name, char, char_name, line in visitor.homoglyphs_found
            ]
        )
        raise SecurityViolation(f"HOMOGLYPH_ATTACK: {msg}")


class AntiHomoglyphGuard:
    """
    Prevents Homoglyph attacks in generated code AST by validating
    all variable, class, and function identifiers against non-Latin scripts.
    """

    def __init__(self, block_mode: bool = True) -> None:
        self.block_mode = block_mode

    def check_code(self, source_code: str) -> bool:
        if not source_code.strip():
            return True

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            # If not parseable as Python, let it pass or fail in other checks
            return True

        try:
            cassandra_validate_identifiers(tree)
        except SecurityViolation as e:
            if self.block_mode:
                logger.error(f"☢️ [SAGA-1] Rejection: {e}")
                raise ValueError(f"SAGA-1 Rejection: {e}") from e
            else:
                logger.warning(f"⚠️ [TAINT] {e}")
                return False

        return True
