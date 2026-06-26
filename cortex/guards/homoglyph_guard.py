# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import ast
import logging
import unicodedata

logger = logging.getLogger("cortex.guards.homoglyph_guard")


class AntiHomoglyphVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.homoglyphs_found: list[tuple[str, str, str, int]] = []

    def check_name(self, name: str, node: ast.AST) -> None:
        for char in name:
            if ord(char) > 127:  # Non-ASCII
                try:
                    char_name = unicodedata.name(char)
                    if any(
                        script in char_name
                        for script in [
                            "CYRILLIC",
                            "GREEK",
                            "ARMENIAN",
                            "HEBREW",
                            "ARABIC",
                            "SYRIAC",
                            "THAANA",
                        ]
                    ):
                        self.homoglyphs_found.append(
                            (name, char, char_name, getattr(node, "lineno", 0))
                        )
                except ValueError:
                    pass

    def visit_Name(self, node: ast.Name) -> None:
        self.check_name(node.id, node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.check_name(node.name, node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.check_name(node.name, node)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self.check_name(node.arg, node)
        self.generic_visit(node)


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
            # Si no es parseable como Python, lo dejamos pasar o dejamos
            # que falle en otros escáneres, esto solo escanea AST válido.
            return True

        visitor = AntiHomoglyphVisitor()
        visitor.visit(tree)

        if visitor.homoglyphs_found:
            msg = "Anti-Homoglyph Guard Triggered: " + ", ".join(
                [
                    f"'{name}' contains '{char}' ({char_name}) at line {line}"
                    for name, char, char_name, line in visitor.homoglyphs_found
                ]
            )
            if self.block_mode:
                logger.error(f"☢️ [SAGA-1] Rejection: {msg}")
                raise ValueError(f"SAGA-1 Rejection: {msg}")
            else:
                logger.warning(f"⚠️ [TAINT] {msg}")
                return False

        return True
