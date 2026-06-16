# [C5-REAL] Exergy-Maximized
"""
CORTEX Autodidact Reverse Engineering Engine (AX-I).
Autonomous deconstruction, structural inference, and behavior synthesis of opaque systems.
"""

import ast
import inspect
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("cortex.forensics.autodidact")


class AutodidactReverseEngineer:
    """
    Sovereign Reverse Engineering & Autodidactic Learning Engine.
    Deconstructs structural code (AST) and infers causal boundaries through empirical probing.
    """

    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id

    def extract_ast_topology(self, source_code: str) -> dict[str, Any]:
        """
        Statically deconstructs Python source code into a causal map of dependencies, 
        classes, methods, and structural logic without arbitrary execution.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return {"status": "SYNTAX_ERROR", "error": str(e)}

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({"name": node.name, "methods": methods})
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module)

        return {
            "status": "DECONSTRUCTED",
            "classes": classes,
            "functions": [f for f in functions if not any(f in c["methods"] for c in classes)],
            "imports": list(set(filter(None, imports)))
        }

    def infer_callable_signature(self, target: Callable) -> dict[str, Any]:
        """
        Empirically analyzes a callable (function/method) to determine its expected
        arguments, types, and return characteristics.
        """
        try:
            sig = inspect.signature(target)
            params = []
            for name, param in sig.parameters.items():
                params.append({
                    "name": name,
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Unknown",
                    "default": str(param.default) if param.default != inspect.Parameter.empty else "None"
                })
                
            return {
                "status": "INFERRED",
                "name": target.__name__,
                "parameters": params,
                "return_type": str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else "Unknown"
            }
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

    def autonomous_empirical_probe(self, target: Callable, test_vectors: list[Any]) -> list[dict[str, Any]]:
        """
        (Autodidact Loop)
        Feeds multiple test vectors into an opaque system to observe outputs, errors,
        and state changes, effectively mapping its operational domain.
        """
        results = []
        for vector in test_vectors:
            try:
                # If target requires kwargs, assume vector is a dict. Otherwise unpack.
                if isinstance(vector, dict):
                    out = target(**vector)
                elif isinstance(vector, (list, tuple)):
                    out = target(*vector)
                else:
                    out = target(vector)
                    
                results.append({
                    "vector": str(vector),
                    "status": "SUCCESS",
                    "output_type": type(out).__name__,
                    "output": str(out)[:200]  # truncate for safety
                })
            except Exception as e:
                results.append({
                    "vector": str(vector),
                    "status": "REJECTED",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
        return results

    def synthesize_knowledge(self, source_code: str, test_target: Callable | None = None, test_vectors: list[Any] | None = None) -> dict[str, Any]:
        """
        Consolidates static AST topography with empirical dynamic probing into a unified 
        zero-entropy structural behavior report.
        """
        logger.info("[Autodidact] Synthesizing structural knowledge")
        report = {
            "static_topology": self.extract_ast_topology(source_code)
        }
        
        if test_target and test_vectors:
            report["dynamic_probe"] = self.autonomous_empirical_probe(test_target, test_vectors)
            report["signature"] = self.infer_callable_signature(test_target)
            
        return report
