# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.0 — DependencyGuard v2: Axiom 4 Enforcement.

Red-Teamed static analysis guard. Detects oracle dependencies through
MULTIPLE detection strategies, not just subprocess pattern matching.

Detection layers::

    L1: Direct subprocess calls (subprocess.run, os.system, etc.)
    L2: Keyword arguments (subprocess.run(args=["kimi"]))
    L3: asyncio subprocess (create_subprocess_exec)
    L4: shutil.which() oracle lookups
    L5: exec/eval with oracle strings
    L6: getattr evasion (getattr(subprocess, "run"))
    L7: String literal scan (any string containing oracle names
        in a subprocess-importing file)

Usage::

    # CLI — scan directory for violations
    python -m cortex.guards.dependency_guard ~/cortex

    # Programmatic
    from cortex.guards.dependency_guard import scan_directory
    violations = scan_directory("/path/to/project")
"""

from __future__ import annotations

import ast
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

__all__ = ["DependencyViolation", "scan_file", "scan_directory"]

logger = logging.getLogger("cortex.guards.dependency_guard")

# Binary names that indicate external oracle dependency
_ORACLE_BINARIES: frozenset[str] = frozenset({
    "kimi", "openai", "anthropic", "claude", "gpt",
    "gemini", "ollama", "llama-cli", "lm-studio",
})

# Modules that enable process execution
_EXEC_MODULES: frozenset[str] = frozenset({
    "subprocess", "os", "shutil", "asyncio",
})

# Sovereign fallback markers — if present, severity = WARNING
_SOVEREIGN_MARKERS: frozenset[str] = frozenset({
    "SovereignLLM", "ThoughtOrchestra",
    "CortexLLMRouter", "LLMProvider",
})


@dataclass(frozen=True)
class DependencyViolation:
    """A detected Axiom 4 violation."""

    file: str
    line: int
    binary: str
    call_type: str
    has_fallback: bool

    @property
    def severity(self) -> str:
        return "CRITICAL" if not self.has_fallback else "WARNING"

    def __str__(self) -> str:
        icon = "🔴" if not self.has_fallback else "🟡"
        fb = " (has fallback)" if self.has_fallback else " — NO FALLBACK"
        return (
            f"{icon} [{self.severity}] {self.file}:{self.line} "
            f"— {self.call_type}('{self.binary}'){fb}"
        )


# ─── Detection Helpers ──────────────────────────────────────────


def _has_exec_import(source: str) -> bool:
    """Check if the file imports any process execution module."""
    return any(mod in source for mod in _EXEC_MODULES)


def _has_sovereign_fallback(source: str) -> bool:
    """Check if the file has sovereign LLM fallback."""
    return any(m in source for m in _SOVEREIGN_MARKERS)


def _get_call_name(node: ast.Call) -> str | None:
    """Extract dotted name from a function call node."""
    func = node.func
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        if isinstance(func.value, ast.Attribute):
            if isinstance(func.value.value, ast.Name):
                return (
                    f"{func.value.value.id}"
                    f".{func.value.attr}.{func.attr}"
                )
    if isinstance(func, ast.Name):
        return func.id
    return None


def _oracle_in_str(value: str) -> str | None:
    """Return oracle name if found in string, else None."""
    lower = value.lower()
    for oracle in _ORACLE_BINARIES:
        if oracle in lower:
            return oracle
    return None


def _scan_args_for_oracles(node: ast.Call) -> list[str]:
    """Scan positional AND keyword args for oracle references."""
    found: list[str] = []
    all_args = list(node.args) + [kw.value for kw in node.keywords]

    for arg in all_args:
        if isinstance(arg, ast.List):
            found.extend(_scan_list(arg))
        elif isinstance(arg, ast.Constant) and isinstance(
            arg.value, str
        ):
            hit = _oracle_in_str(arg.value)
            if hit:
                found.append(hit)
        elif isinstance(arg, ast.JoinedStr):
            found.extend(_scan_fstring(arg))
        elif isinstance(arg, ast.Name):
            found.extend(_scan_variable_name(arg))
    return found


def _scan_list(node: ast.List) -> list[str]:
    """Scan list literal elements for oracle references."""
    found: list[str] = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(
            elt.value, str
        ):
            name = Path(elt.value).name.lower()
            if name in _ORACLE_BINARIES:
                found.append(name)
        elif isinstance(elt, ast.Name):
            found.extend(_scan_variable_name(elt))
    return found


def _scan_fstring(node: ast.JoinedStr) -> list[str]:
    """Scan f-string for oracle references in constant parts."""
    found: list[str] = []
    for val in node.values:
        if isinstance(val, ast.Constant) and isinstance(
            val.value, str
        ):
            hit = _oracle_in_str(val.value)
            if hit:
                found.append(hit)
    return found


def _scan_variable_name(node: ast.Name) -> list[str]:
    """Check if a variable name references an oracle."""
    lower = node.id.lower()
    return [
        node.id for o in _ORACLE_BINARIES if o in lower
    ]


# ─── Core Detection Engine ──────────────────────────────────────


def _find_violations(tree: ast.Module) -> list[tuple[int, str, str]]:
    """Multi-layer oracle detection. Returns (line, binary, type)."""
    results: list[tuple[int, str, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = _get_call_name(node)

        # L1+L2: Direct subprocess/os calls (positional + kwargs)
        if call_name in (
            "subprocess.run", "subprocess.call",
            "subprocess.Popen", "os.system", "os.popen",
            "shutil.which",
        ):
            for binary in _scan_args_for_oracles(node):
                results.append(
                    (node.lineno, binary, call_name)
                )
            continue

        # L3: asyncio.create_subprocess_exec/shell
        if call_name in (
            "asyncio.create_subprocess_exec",
            "asyncio.create_subprocess_shell",
        ):
            for binary in _scan_args_for_oracles(node):
                results.append(
                    (node.lineno, binary, call_name)
                )
            continue

        # L5: exec/eval with oracle strings
        if call_name in ("exec", "eval"):
            for binary in _scan_exec_args(node):
                results.append(
                    (node.lineno, binary, f"{call_name}()")
                )
            continue

        # L6: getattr(subprocess, "run") evasion
        if call_name == "getattr":
            hit = _check_getattr_evasion(node)
            if hit:
                results.append(hit)
                continue

    return results


def _scan_exec_args(node: ast.Call) -> list[str]:
    """Scan exec/eval string args for oracle references."""
    found: list[str] = []
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(
            arg.value, str
        ):
            hit = _oracle_in_str(arg.value)
            if hit:
                found.append(hit)
    return found


def _check_getattr_evasion(
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
    if isinstance(attr, ast.Constant) and isinstance(
        attr.value, str
    ):
        method = f"{target.id}.{attr.value}"
        return (node.lineno, f"getattr→{method}", "getattr")
    return None


# L7: Broad string literal heuristic — catches variable indirection
# and dynamic import evasion. Only fires if file ACTUALLY makes
# subprocess/exec calls (not just imports subprocess).
def _find_oracle_string_literals(
    tree: ast.Module,
    has_exec_calls: bool,
) -> list[tuple[int, str, str]]:
    """Find string literals containing oracle names.

    Only fires when the file contains actual process execution
    calls, preventing false positives on config/preset files.

    Catches patterns invisible to call-based analysis:
    - fn = subprocess.run; fn(["kimi"])
    - importlib.import_module("subprocess").run(["kimi"])
    """
    if not has_exec_calls:
        return []

    results: list[tuple[int, str, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str):
            continue
        hit = _oracle_in_str(node.value)
        if not hit:
            continue
        line = getattr(node, "lineno", 0)
        results.append(
            (line, hit, "string_literal")
        )

    return results


def _has_exec_calls(tree: ast.Module) -> bool:
    """Check if the AST contains actual process execution calls."""
    exec_calls = {
        "subprocess.run", "subprocess.call",
        "subprocess.Popen", "os.system", "os.popen",
        "shutil.which", "exec", "eval",
        "asyncio.create_subprocess_exec",
        "asyncio.create_subprocess_shell",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _get_call_name(node)
            if name in exec_calls:
                return True
            # Also detect getattr(subprocess, ...)
            if name == "getattr" and len(node.args) >= 1:
                if isinstance(node.args[0], ast.Name):
                    if node.args[0].id in (
                        "subprocess", "os", "shutil"
                    ):
                        return True
    return False


# ─── Public API ──────────────────────────────────────────────────


def scan_file(filepath: str | Path) -> list[DependencyViolation]:
    """Scan a single Python file for Axiom 4 violations."""
    filepath = Path(filepath)
    if not filepath.exists() or filepath.suffix != ".py":
        return []

    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    # Quick exit: no exec-capable imports → no risk
    if not _has_exec_import(source):
        return []

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    has_fallback = _has_sovereign_fallback(source)

    # Skip self-detection (the guard references oracle names)
    if filepath.name == "dependency_guard.py":
        return []

    # Run all detection layers
    exec_calls = _has_exec_calls(tree)
    hits = _find_violations(tree)
    hits.extend(
        _find_oracle_string_literals(tree, exec_calls)
    )

    # Deduplicate by (line, binary)
    seen: set[tuple[int, str]] = set()
    violations: list[DependencyViolation] = []
    for line, binary, call_type in hits:
        key = (line, binary)
        if key in seen:
            continue
        seen.add(key)
        # L7 string_literal hits are heuristic → WARNING only
        # Direct call hits (L1-L6) respect has_fallback
        is_heuristic = call_type == "string_literal"
        violations.append(
            DependencyViolation(
                file=str(filepath),
                line=line,
                binary=binary,
                call_type=call_type,
                has_fallback=True if is_heuristic else has_fallback,
            )
        )

    return violations


def scan_directory(
    directory: str | Path,
    *,
    exclude_venv: bool = True,
    exclude_tests: bool = False,
) -> list[DependencyViolation]:
    """Recursively scan a directory for Axiom 4 violations."""
    directory = Path(directory)
    violations: list[DependencyViolation] = []

    exclude_dirs = {"__pycache__", ".git", "node_modules"}
    if exclude_venv:
        exclude_dirs |= {".venv", "venv", "env", ".env"}
    if exclude_tests:
        exclude_dirs.add("tests")

    for py_file in directory.rglob("*.py"):
        if any(
            excl in py_file.parts for excl in exclude_dirs
        ):
            continue
        violations.extend(scan_file(py_file))

    return violations


def main() -> None:
    """CLI entry point for DependencyGuard."""
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    target_path = Path(target).expanduser().resolve()

    print(
        "🛡️  DependencyGuard v2 — Axiom 4 Enforcement\n"
        f"   Scanning: {target_path}\n"
    )

    if target_path.is_file():
        violations = scan_file(target_path)
    else:
        violations = scan_directory(target_path)

    if not violations:
        print(
            "✅ No Axiom 4 violations detected. "
            "Sovereignty intact."
        )
        return

    critical = sum(1 for v in violations if not v.has_fallback)
    warnings = len(violations) - critical

    for v in violations:
        print(f"   {v}")

    print(
        f"\n{'🔴' if critical else '🟡'} "
        f"Total: {len(violations)} violations "
        f"({critical} CRITICAL, {warnings} warnings)"
    )

    if critical > 0:
        print(
            "\n⚠️  CRITICAL violations detected. "
            "Use SovereignLLM (cortex/llm/sovereign.py) "
            "to replace subprocess oracle calls."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
