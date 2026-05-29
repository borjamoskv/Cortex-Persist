import ast
import inspect
from typing import Any


class CortexASTParser:
    """
    C5-REAL AST Parser for the Self-Modifying Topology Engine (SMTE).
    Transcribes Python source code into mutable AST structures to prepare for Autopoietic mutation.
    """

    def __init__(self, target_module_path: str):
        self.target_module_path = target_module_path
        self.source_code = ""
        self.tree = None
        self._load()

    def _load(self):
        with open(self.target_module_path, encoding="utf-8") as f:
            self.source_code = f.read()
        self.tree = ast.parse(self.source_code)

    def extract_functions(self) -> list[dict[str, Any]]:
        """Extracts all function definitions from the AST."""
        functions = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append(
                    {
                        "name": node.name,
                        "lineno": node.lineno,
                        "end_lineno": node.end_lineno,
                        "body": node.body,
                    }
                )
        return functions

    def extract_classes(self) -> list[dict[str, Any]]:
        """Extracts all class definitions from the AST."""
        classes = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                classes.append(
                    {
                        "name": node.name,
                        "lineno": node.lineno,
                        "end_lineno": node.end_lineno,
                        "methods": [
                            n.name
                            for n in node.body
                            if isinstance(n, ast.FunctionDef) or isinstance(n, ast.AsyncFunctionDef)
                        ],
                    }
                )
        return classes

    def get_source_segment(self, start_line: int, end_line: int) -> str:
        """Returns the raw source code string for a given line range."""
        lines = self.source_code.splitlines()
        # 1-indexed to 0-indexed translation
        return "\\n".join(lines[start_line - 1 : end_line])

    def inject_mutation(self, original_segment: str, mutated_segment: str) -> str:
        """
        Replaces the original segment with the mutated segment.
        Returns the new source code.
        """
        if original_segment not in self.source_code:
            raise ValueError("Target segment not found in source code. Entropy misalignment.")

        self.source_code = self.source_code.replace(original_segment, mutated_segment)
        # Verify the new source code parses correctly
        try:
            self.tree = ast.parse(self.source_code)
        except SyntaxError as e:
            raise ValueError(f"Mutation resulted in invalid syntax: {e}")

        return self.source_code

    def save(self):
        """Commits the current source_code to disk."""
        with open(self.target_module_path, "w", encoding="utf-8") as f:
            f.write(self.source_code)
