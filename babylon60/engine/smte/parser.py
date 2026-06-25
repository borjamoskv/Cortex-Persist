# [C5-REAL] Exergy-Maximized
"""
CORTEX - SMTE AST Parser (Transcription)
Axiom Ω₁₄: Code as DNA.
Parses, analyzes, and reconstructs Python source code for mutation.
"""

import ast
import logging
from typing import Any

logger = logging.getLogger("babylon60.engine.smte.parser")


class AgentASTParser:
    """
    Transcription engine for SMTE. Loads Python source code into memory
    as an Abstract Syntax Tree (AST), allowing LLM-driven structural mutations.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.source_code = self._load_source()
        self.tree = ast.parse(self.source_code, filename=self.filepath)

    def _load_source(self) -> str:
        with open(self.filepath, encoding="utf-8") as f:
            return f.read()

    def get_topology(self) -> dict[str, Any]:
        """
        Extracts the structural topology (classes, functions, docs) of the agent.
        """
        topology = {"classes": [], "functions": []}

        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.ClassDef):
                topology["classes"].append(
                    {
                        "name": node.name,
                        "docstring": ast.get_docstring(node),
                        "methods": [
                            n.name
                            for n in node.body
                            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
                        ],
                    }
                )
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                topology["functions"].append(
                    {"name": node.name, "docstring": ast.get_docstring(node)}
                )

        return topology

    def apply_mutation(self, mutator_func) -> bool:
        """
        Applies a mutation function to the AST and validates structural integrity.
        mutator_func(ast.AST) -> bool (True if changed)
        """
        if mutator_func(self.tree):
            # Verify the tree is still valid Python
            ast.fix_missing_locations(self.tree)
            try:
                compile(self.tree, filename=self.filepath, mode="exec")
                return True
            except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
                logger.error(f"Mutation failed compilation check: {e}")
                return False
        return False

    def crystallize(self, output_path: str = None) -> str:  # pyright: ignore[reportArgumentType]
        """
        Writes the mutated AST back to physical disk. (C5-REAL).
        """
        target_path = output_path or self.filepath
        new_source = ast.unparse(self.tree)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_source)

        logger.info(f"SMTE: Rewrote agent DNA to {target_path}")
        return new_source
