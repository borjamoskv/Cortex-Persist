import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def get_call_name(node: ast.Call) -> str | None:
    """Extract dotted name from a function call node."""
    func = node.func
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        if isinstance(func.value, ast.Attribute):
            if isinstance(func.value.value, ast.Name):
                return f"{func.value.value.id}.{func.value.attr}.{func.attr}"
    if isinstance(func, ast.Name):
        return func.id
    return None


def scan_exec_args(node: ast.Call) -> list[str]:
    """Scan exec/eval string args for oracle references."""
    from cortex.guards.scanners.literals import oracle_in_str

    found: list[str] = []
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            hit = oracle_in_str(arg.value)
            if hit:
                found.append(hit)
    return found


def check_getattr_evasion(node: ast.Call) -> tuple[int, str, str] | None:
    """Detect getattr(subprocess, "run")([oracle]) pattern."""
    if len(node.args) < 2:
        return None
    target, attr = node.args[0], node.args[1]
    if not isinstance(target, ast.Name):
        return None
    if target.id not in ("subprocess", "os", "shutil"):
        return None
    if isinstance(attr, ast.Constant) and isinstance(attr.value, str):
        method = f"{target.id}.{attr.value}"
        return (node.lineno, f"getattr\u2192{method}", "getattr")
    return None


class CallsScanner:
    """Scanner for process execution and evasion calls."""

    EXEC_CALLS = {
        "subprocess.run",
        "subprocess.call",
        "subprocess.Popen",
        "os.system",
        "os.popen",
        "shutil.which",
        "exec",
        "eval",
        "asyncio.create_subprocess_exec",
        "asyncio.create_subprocess_shell",
    }

    def scan(self, node: ast.AST) -> list[tuple[int, str, str]]:
        from cortex.guards.scanners.literals import scan_args_for_oracles

        results = []
        if isinstance(node, ast.Call):
            call_name = get_call_name(node)

            if call_name in self.EXEC_CALLS:
                if call_name in ("exec", "eval"):
                    for binary in scan_exec_args(node):
                        results.append((node.lineno, binary, f"{call_name}()"))
                else:
                    for binary in scan_args_for_oracles(node):
                        results.append((node.lineno, binary, str(call_name)))

            elif call_name == "getattr":
                hit = check_getattr_evasion(node)
                if hit:
                    results.append(hit)

        return results
