import ast
from pathlib import Path

from cortex.guards.models import EXEC_MODULES, ORACLE_BINARIES, SOVEREIGN_MARKERS


def has_exec_import(source: str) -> bool:
    """Check if the file imports any process execution module."""
    return any(mod in source for mod in EXEC_MODULES)


def has_sovereign_fallback(source: str) -> bool:
    """Check if the file has sovereign LLM fallback."""
    return any(m in source for m in SOVEREIGN_MARKERS)


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


def oracle_in_str(value: str) -> str | None:
    """Return oracle name if found in string, else None."""
    lower = value.lower()
    for oracle in ORACLE_BINARIES:
        if oracle in lower:
            return oracle
    return None


def scan_args_for_oracles(node: ast.Call) -> list[str]:
    """Scan positional AND keyword args for oracle references."""
    found: list[str] = []
    all_args = list(node.args) + [kw.value for kw in node.keywords]

    for arg in all_args:
        if isinstance(arg, ast.List):
            found.extend(scan_list(arg))
        elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            hit = oracle_in_str(arg.value)
            if hit:
                found.append(hit)
        elif isinstance(arg, ast.JoinedStr):
            found.extend(scan_fstring(arg))
        elif isinstance(arg, ast.Name):
            found.extend(scan_variable_name(arg))
    return found


def scan_list(node: ast.List) -> list[str]:
    """Scan list literal elements for oracle references."""
    found: list[str] = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            name = Path(elt.value).name.lower()
            if name in ORACLE_BINARIES:
                found.append(name)
        elif isinstance(elt, ast.Name):
            found.extend(scan_variable_name(elt))
    return found


def scan_fstring(node: ast.JoinedStr) -> list[str]:
    """Scan f-string for oracle references in constant parts."""
    found: list[str] = []
    for val in node.values:
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            hit = oracle_in_str(val.value)
            if hit:
                found.append(hit)
    return found


def scan_variable_name(node: ast.Name) -> list[str]:
    """Check if a variable name references an oracle."""
    lower = node.id.lower()
    return [node.id for o in ORACLE_BINARIES if o in lower]


def find_violations(tree: ast.Module) -> list[tuple[int, str, str]]:
    """Multi-layer oracle detection. Returns (line, binary, type)."""
    results: list[tuple[int, str, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = get_call_name(node)

        # L1+L2: Direct subprocess/os calls (positional + kwargs)
        if call_name in (
            "subprocess.run",
            "subprocess.call",
            "subprocess.Popen",
            "os.system",
            "os.popen",
            "shutil.which",
        ):
            for binary in scan_args_for_oracles(node):
                results.append((node.lineno, binary, call_name))
            continue

        # L3: asyncio.create_subprocess_exec/shell
        if call_name in (
            "asyncio.create_subprocess_exec",
            "asyncio.create_subprocess_shell",
        ):
            for binary in scan_args_for_oracles(node):
                results.append((node.lineno, binary, call_name))
            continue

        # L5: exec/eval with oracle strings
        if call_name in ("exec", "eval"):
            for binary in scan_exec_args(node):
                results.append((node.lineno, binary, f"{call_name}()"))
            continue

        # L6: getattr(subprocess, "run") evasion
        if call_name == "getattr":
            hit = check_getattr_evasion(node)
            if hit:
                results.append(hit)
                continue

    return results


def scan_exec_args(node: ast.Call) -> list[str]:
    """Scan exec/eval string args for oracle references."""
    found: list[str] = []
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            hit = oracle_in_str(arg.value)
            if hit:
                found.append(hit)
    return found


def check_getattr_evasion(
    node: ast.Call,
) -> tuple[int, str, str] | None:
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


def find_oracle_string_literals(
    tree: ast.Module,
    has_exec_calls: bool,
) -> list[tuple[int, str, str]]:
    """Find string literals containing oracle names.
    Catches patterns invisible to call-based analysis.
    """
    if not has_exec_calls:
        return []

    results: list[tuple[int, str, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str):
            continue
        hit = oracle_in_str(node.value)
        if not hit:
            continue
        line = getattr(node, "lineno", 0)
        results.append((line, hit, "string_literal"))

    return results


def has_exec_calls(tree: ast.Module) -> bool:
    """Check if the AST contains actual process execution calls."""
    exec_calls = {
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
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = get_call_name(node)
            if name in exec_calls:
                return True
            # Also detect getattr(subprocess, ...)
            if name == "getattr" and len(node.args) >= 1:
                if isinstance(node.args[0], ast.Name):
                    if node.args[0].id in ("subprocess", "os", "shutil"):
                        return True
    return False
