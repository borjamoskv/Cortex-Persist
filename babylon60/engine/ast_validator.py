import ast
import logging

logger = logging.getLogger("babylon60.engine.ast_validator")

class StrictASTValidator(ast.NodeVisitor):
    """
    [C5-REAL] Strict AST Validator.
    Enforces CORTEX-Persist invariants structurally before AST projection/execution.
    Rejects entropy and anergy directly at the syntax tree level.
    """
    def __init__(self, filename: str = "<unknown>"):
        self.filename = filename
        self.errors: list[tuple[int, str]] = []
        self._in_async_func = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        old_in_async = self._in_async_func
        self._in_async_func = True
        self._check_float_annotations(node)
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

        # Rule: No explicit float() conversions
        if isinstance(node.func, ast.Name) and node.func.id == "float":
            self._record_error(node, "[CRITICAL] Explicit float() conversion detected. Use Babylon60.from_int() or integer arithmetic.")

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Rule: No bare except Exception:
        if node.type is None:
            self._record_error(node, "[MEDIUM] Bare `except Exception:` clause detected. Narrow exception scoping required.")
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            self._record_error(node, "[MEDIUM] Catching base `Exception` detected. Narrow exception scoping required.")
            
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        # Rule: BABYLON-60. No float or float64 in internal calculations.
        if isinstance(node.value, float):
            self._record_error(node, "[CRITICAL] Float literal detected. BABYLON-60 Epistemology requires integer structs scaled to Base-60 to avoid floating point entropy.")
            
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Rule: No float in type annotations
        self._check_float_annotations(node)
        self.generic_visit(node)

    def _check_float_annotations(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Detect float in function parameter annotations and return type."""
        # Check return annotation
        if node.returns and self._annotation_contains_float(node.returns):
            self._record_error(node, "[CRITICAL] Float return annotation detected. BABYLON-60 requires integer/Babylon60 return types.")
        # Check argument annotations
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if arg.annotation and self._annotation_contains_float(arg.annotation):
                self._record_error(arg, f"[CRITICAL] Float annotation on parameter '{arg.arg}'. BABYLON-60 requires integer/Babylon60 types.")

    def _annotation_contains_float(self, annotation: ast.AST) -> bool:
        """Check if an annotation AST node references 'float'."""
        if isinstance(annotation, ast.Name) and annotation.id == "float":
            return True
        if isinstance(annotation, ast.Constant) and annotation.value == "float":
            return True
        # Check inside subscripts like Optional[float], list[float]
        if isinstance(annotation, ast.Subscript):
            return self._annotation_contains_float(annotation.slice)
        if isinstance(annotation, ast.Tuple):
            return any(self._annotation_contains_float(e) for e in annotation.elts)
        # BinOp for X | Y union syntax (Python 3.10+)
        if isinstance(annotation, ast.BinOp):
            return (self._annotation_contains_float(annotation.left)
                    or self._annotation_contains_float(annotation.right))
        return False

    def visit_BinOp(self, node: ast.BinOp):
        # Rule: Flag true division '/' in numeric contexts (produces float)
        if isinstance(node.op, ast.Div):
            self._record_error(node, "[WARNING] True division '/' detected — produces float in Python 3. Use '//' (floor division) or Babylon60.div() for integer math.")
        self.generic_visit(node)

    def _record_error(self, node: ast.AST, msg: str):
        line = getattr(node, "lineno", -1)
        self.errors.append((line, msg))

def validate_ast(source_code: str, filename: str = "<unknown>") -> list[tuple[int, str]]:
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
