# [C5-REAL] Exergy-Maximized
import ast


def calculate_ast_complexity(source_code: str) -> float:
    """
    Calculates a basic cyclomatic complexity metric by counting branching nodes.
    Base complexity is 1.0. Each branch adds 1.0.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return 10.0  # High complexity penalty for syntax errors

    complexity = 1.0
    for node in ast.walk(tree):
        if isinstance(
            node, ast.If | ast.For | ast.While | ast.Try | ast.ExceptHandler | ast.With | ast.Match
        ):
            complexity += 1.0
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1

    return complexity


def estimate_dead_code_ratio(source_code: str) -> float:
    """
    Statically estimates the dead code ratio.
    Looks for unreachable statements (e.g. after return/raise)
    or simple placeholder functions (e.g. just 'pass').
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return 1.0

    total_nodes = 0
    dead_nodes = 0

    for node in ast.walk(tree):
        total_nodes += 1
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # Check if function is empty or just 'pass'
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                # The whole body is dead weight
                dead_nodes += 2

        # Check for unreachable code after return/raise/break/continue
        if hasattr(node, "body") and isinstance(node.body, list):  # pyright: ignore[reportAttributeAccessIssue]
            found_terminator = False
            for stmt in node.body:  # pyright: ignore[reportAttributeAccessIssue]
                if found_terminator:
                    dead_nodes += sum(1 for _ in ast.walk(stmt))
                if isinstance(stmt, ast.Return | ast.Raise | ast.Break | ast.Continue):
                    found_terminator = True

    if total_nodes == 0:
        return 0.0

    return min(1.0, dead_nodes / total_nodes)
