# [C5-REAL] Exergy-Maximized
"""
Sovereign AST Signer (Evidence Hash).

Generates a deterministic cryptographic signature (SHA3-256) of a Python source file's
Abstract Syntax Tree (AST), ignoring comments, formatting, and docstrings.
"""

import ast
import hashlib


class _DocstringRemover(ast.NodeTransformer):
    """Removes docstrings from AST nodes to ensure semantic-only hashing."""
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        return node

    def visit_Module(self, node: ast.Module) -> ast.Module:
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        return node

def generate_ast_signature(code: str) -> str:
    """
    Generate a deterministic SHA3-256 signature based on the AST of the Python code.
    If the code is not valid Python, falls back to a standard SHA3-256 hash of the raw text.
    """
    try:
        tree = ast.parse(code)
        tree = _DocstringRemover().visit(tree)
        # Using ast.dump for a deterministic string representation of the tree structure.
        # include_attributes=False ensures line numbers are ignored.
        ast_string = ast.dump(tree, annotate_fields=True, include_attributes=False)
        hash_digest = hashlib.sha3_256(ast_string.encode('utf-8')).hexdigest()
        return f"ast_sha3_256:{hash_digest}"
    except SyntaxError:
        # Fallback for non-Python code or unparseable code
        hash_digest = hashlib.sha3_256(code.encode('utf-8')).hexdigest()
        return f"raw_sha3_256:{hash_digest}"
