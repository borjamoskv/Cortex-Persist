# [C5-REAL] Exergy-Maximized
import ast
import logging
from typing import Any

logger = logging.getLogger(__name__)

class LandauerCompressor:
    """
    Thermodynamic Context Compression (Landauer API).
    Purges narrative noise, Green Theater, and non-causal code before LLM ingestion.
    Reduces TTFT (Time-To-First-Token) and enforces the C5-REAL execution baseline.
    """

    @staticmethod
    def compress_ast(source_code: str) -> str:
        """
        Parses the source code, removes narrative docstrings, and strips non-causal prints.
        Returns structurally invariant code with reduced thermodynamic footprint.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            # If not valid Python, fallback to raw return to prevent destructive data loss
            return source_code

        # AST Walker to mutate non-causal nodes
        class AnergyPurger(ast.NodeTransformer):
            def visit_Expr(self, node: ast.Expr) -> Any:
                # Remove top-level strings (usually docstrings)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    return None

                # Remove print() and logger.*() / logging.*() calls
                if isinstance(node.value, ast.Call):
                    func = node.value.func
                    if isinstance(func, ast.Name) and func.id == 'print':
                        return None
                    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                        if func.value.id in ['logger', 'logging']:
                            return None

                return self.generic_visit(node)

            def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
                # Recursively visit first to process docstrings inside
                self.generic_visit(node)
                # Remove function docstrings if they exist as first node
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                    if isinstance(node.body[0].value.value, str):
                        node.body.pop(0)
                return node

            def visit_ClassDef(self, node: ast.ClassDef) -> Any:
                self.generic_visit(node)
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                    if isinstance(node.body[0].value.value, str):
                        node.body.pop(0)
                return node

        purger = AnergyPurger()
        purified_tree = purger.visit(tree)
        ast.fix_missing_locations(purified_tree)

        # Unparse requires Python 3.9+
        try:
            compressed_code = ast.unparse(purified_tree)
            return compressed_code
        except Exception as e:
            logger.error(f"Landauer API Unparse Error: {e}")
            return source_code

    @classmethod
    def apply_compression(cls, payload: str, modality: str = "text") -> str:
        """
        Entrypoint for the Landauer compression pipeline.
        """
        logger.info("[Landauer API] Initiating Thermodynamic Context Compression.")
        if modality == "python_code":
            return cls.compress_ast(payload)
        # Add additional modality compressors (JSON, text) as needed
        return payload
