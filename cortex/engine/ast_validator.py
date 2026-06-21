import ast
import logging
from typing import List, Tuple

logger = logging.getLogger("cortex.engine.ast_validator")

class StrictASTValidator(ast.NodeVisitor):
    """
    [C5-REAL] Strict AST Validator.
    Enforces CORTEX-Persist invariants structurally before AST projection/execution.
    Rejects entropy and anergy directly at the syntax tree level.
    """
    def __init__(self, filename: str = "<unknown>"):
        self.filename = filename
        self.errors: List[Tuple[int, str]] = []
        self._in_async_func = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        old_in_async = self._in_async_func
        self._in_async_func = True
        self.generic_visit(node)
        self._in_async_func = old_in_async

    def visit_Call(self, node: ast.Call):
        # Rule: No time.sleep() inside async def
        if self._in_async_func:
            if isinstance(node.func, ast.Attribute) and getattr(node.func.value, "id", None) == "time" and node.func.attr == "sleep":
                self._record_error(node, "[CRITICAL] time.sleep() inside async def is a thermodynamic dead-lock. Use asyncio.sleep().")
        
        # Rule: No bare print() in engine/ core paths (enforced strictly here)
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self._record_error(node, "[MEDIUM] Bare print() detected. Use structured logging via logging.getLogger().")

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Rule: No bare except Exception:
        if node.type is None:
            self._record_error(node, "[MEDIUM] Bare `except:` clause detected. Narrow exception scoping required.")
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            self._record_error(node, "[MEDIUM] Catching base `Exception` detected. Narrow exception scoping required.")
            
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        # Rule: BABYLON-60. No float or float64 in internal calculations.
        if isinstance(node.value, float):
            self._record_error(node, "[CRITICAL] Float literal detected. BABYLON-60 Epistemology requires integer structs scaled to Base-60 to avoid floating point entropy.")
            
        self.generic_visit(node)

    def _record_error(self, node: ast.AST, msg: str):
        line = getattr(node, "lineno", -1)
        self.errors.append((line, msg))

def validate_ast(source_code: str, filename: str = "<unknown>") -> List[Tuple[int, str]]:
    """
    Parses and validates the source code against C5-REAL invariants.
    Returns a list of (line_number, error_message) tuples.
    If the list is empty, the AST is structurally pure.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return [(e.lineno or -1, f"[FATAL] SyntaxError: {e.msg}")]
        
    validator = StrictASTValidator(filename)
    validator.visit(tree)
    
    return validator.errors

def enforce_strict_types(source_code: str, filename: str = "<unknown>") -> None:
    """
    Fails hard if any C5-REAL structural invariant is violated.
    """
    errors = validate_ast(source_code, filename)
    if errors:
        error_report = "\n".join([f"Line {line}: {msg}" for line, msg in errors])
        logger.error(f"AST Structural P0 Failure in {filename}:\n{error_report}")
        raise ValueError(f"AST Structural Validation Failed (C5-REAL Enforced):\n{error_report}")
