"""CORTEX — AST Validator (Static Analysis Gate).

Extracted from code_smith.py for module splitting (Ω₂: LOC ≤ 500).

Parses code into an AST and enforces:
    1. Node whitelist:     No forbidden AST node types.
    2. Call blacklist:     No eval, exec, os.system, etc.
    3. Import audit:       Only whitelisted module prefixes.
    4. Complexity guard:   Loop depth, function size, cyclomatic complexity.

DECISION: Ω₃ + Ω₂ → AST-level analysis is the only trustworthy gate
for LLM-generated code. String-matching is trivially bypassable.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

# ── Constants ──────────────────────────────────────────────────────────────

# AST nodes that are NEVER allowed in generated code (Ω₃: Zero Trust)
FORBIDDEN_AST_NODES: frozenset[type] = frozenset(
    {
        ast.Global,  # No global state mutation
    }
)

# Function calls that are categorically banned
FORBIDDEN_CALLS: frozenset[str] = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "globals",
        "locals",
        "breakpoint",
        "exit",
        "quit",
    }
)

# Module imports that require explicit whitelisting
FORBIDDEN_IMPORTS: frozenset[str] = frozenset(
    {
        "os",
        "subprocess",
        "shutil",
        "sys",
        "ctypes",
        "importlib",
        "signal",
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "aiohttp",
        "pickle",
        "shelve",
        "marshal",
        "code",
        "codeop",
        "compileall",
    }
)

# Whitelisted imports (safe standard library + cortex internals)
ALLOWED_IMPORT_PREFIXES: frozenset[str] = frozenset(
    {
        "typing",
        "collections",
        "dataclasses",
        "enum",
        "functools",
        "itertools",
        "math",
        "hashlib",
        "json",
        "re",
        "abc",
        "logging",
        "time",
        "datetime",
        "pathlib",
        "cortex.",
        "pydantic",
    }
)

# Complexity ceilings
MAX_LOOP_DEPTH: int = 4
MAX_FUNCTION_LINES: int = 80
MAX_TOTAL_LINES: int = 500
MAX_CYCLOMATIC_COMPLEXITY: int = 15


# ── Enums ──────────────────────────────────────────────────────────────────


class ValidationVerdict(str, Enum):
    """Result of AST validation gate."""

    PASS = "pass"
    FAIL_FORBIDDEN_NODE = "fail_forbidden_node"
    FAIL_FORBIDDEN_CALL = "fail_forbidden_call"
    FAIL_FORBIDDEN_IMPORT = "fail_forbidden_import"
    FAIL_COMPLEXITY = "fail_complexity"
    FAIL_SYNTAX = "fail_syntax"
    FAIL_PARSE = "fail_parse"


# ── Data Model ─────────────────────────────────────────────────────────────


@dataclass()
class ASTValidationResult:
    """Detailed result of the Static Analysis Gate."""

    verdict: ValidationVerdict
    violations: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.verdict == ValidationVerdict.PASS

    def summary(self) -> str:
        if self.passed:
            return f"✅ AST validation passed. Stats: {self.stats}"
        return f"❌ {self.verdict.value}: {'; '.join(self.violations)}"


# ── ASTValidator ───────────────────────────────────────────────────────────


class ASTValidator:
    """The Static Analysis Gate (SAG).

    Parses code into an AST and enforces:
        1. Node whitelist:     No forbidden AST node types.
        2. Call blacklist:     No eval, exec, os.system, etc.
        3. Import audit:       Only whitelisted module prefixes.
        4. Complexity guard:   Loop depth, function size, cyclomatic complexity.
    """

    __slots__ = ("_allowed_import_prefixes", "_forbidden_calls", "_forbidden_imports")

    def __init__(
        self,
        *,
        allowed_import_prefixes: Optional[frozenset[str]] = None,
        forbidden_calls: Optional[frozenset[str]] = None,
        forbidden_imports: Optional[frozenset[str]] = None,
    ) -> None:
        self._allowed_import_prefixes = allowed_import_prefixes or ALLOWED_IMPORT_PREFIXES
        self._forbidden_calls = forbidden_calls or FORBIDDEN_CALLS
        self._forbidden_imports = forbidden_imports or FORBIDDEN_IMPORTS

    def validate(self, code: str) -> ASTValidationResult:
        """Run the full Static Analysis Gate on Python source code."""
        # Phase 1: Parse
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_SYNTAX,
                violations=[f"SyntaxError at line {e.lineno}: {e.msg}"],
            )

        # Phase 2: Forbidden AST nodes
        node_violations = _check_forbidden_nodes(tree)
        if node_violations:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_FORBIDDEN_NODE,
                violations=node_violations,
            )

        # Phase 3: Forbidden function calls
        call_violations = self._check_calls(tree)
        if call_violations:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_FORBIDDEN_CALL,
                violations=call_violations,
            )

        # Phase 4: Import audit
        import_violations = self._check_imports(tree)
        if import_violations:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_FORBIDDEN_IMPORT,
                violations=import_violations,
            )

        # Phase 5: Complexity guard
        complexity_violations, stats = _check_complexity(tree, code)
        if complexity_violations:
            return ASTValidationResult(
                verdict=ValidationVerdict.FAIL_COMPLEXITY,
                violations=complexity_violations,
                stats=stats,
            )

        return ASTValidationResult(verdict=ValidationVerdict.PASS, stats=stats)

    def _check_calls(self, tree: ast.AST) -> list[str]:
        """Detect banned function calls in the AST."""
        violations: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _extract_call_name(node)
            if call_name and call_name in self._forbidden_calls:
                violations.append(
                    f"Forbidden call: {call_name}() at line {getattr(node, 'lineno', '?')}"
                )
        return violations

    def _check_imports(self, tree: ast.AST) -> list[str]:
        """Audit all imports against whitelist."""
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not self._is_import_allowed(alias.name):
                        violations.append(f"Forbidden import: '{alias.name}' at line {node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if not self._is_import_allowed(module):
                    violations.append(f"Forbidden import: 'from {module}' at line {node.lineno}")
        return violations

    def _is_import_allowed(self, module_name: str) -> bool:
        """Check if a module import is whitelisted."""
        base_module = module_name.split(".")[0]
        if base_module in self._forbidden_imports:
            return False
        return any(
            module_name == prefix or module_name.startswith(prefix)
            for prefix in self._allowed_import_prefixes
        )


# ── Extracted pure functions ───────────────────────────────────────────────


def _extract_call_name(node: ast.Call) -> Optional[str]:
    """Extract the function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _check_forbidden_nodes(tree: ast.AST) -> list[str]:
    """Check for forbidden AST node types."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if type(node) in FORBIDDEN_AST_NODES:
            violations.append(
                f"Forbidden AST node: {type(node).__name__} at line {getattr(node, 'lineno', '?')}"
            )
    return violations


def _check_complexity(
    tree: ast.AST,
    code: str,
) -> tuple[list[str], dict[str, Any]]:
    """Enforce complexity ceilings."""
    violations: list[str] = []
    lines = code.strip().split("\n")
    total_lines = len(lines)

    stats: dict[str, Any] = {
        "total_lines": total_lines,
        "functions": 0,
        "classes": 0,
        "max_loop_depth": 0,
        "max_function_lines": 0,
    }

    if total_lines > MAX_TOTAL_LINES:
        violations.append(f"Total lines ({total_lines}) exceeds maximum ({MAX_TOTAL_LINES})")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stats["functions"] += 1
            func_lines = (node.end_lineno or node.lineno) - node.lineno + 1
            stats["max_function_lines"] = max(stats["max_function_lines"], func_lines)

            if func_lines > MAX_FUNCTION_LINES:
                violations.append(
                    f"Function '{node.name}' has {func_lines} lines (max {MAX_FUNCTION_LINES})"
                )

            complexity = cyclomatic_complexity(node)
            if complexity > MAX_CYCLOMATIC_COMPLEXITY:
                violations.append(
                    f"Function '{node.name}' cyclomatic "
                    f"complexity {complexity} > "
                    f"{MAX_CYCLOMATIC_COMPLEXITY}"
                )

        elif isinstance(node, ast.ClassDef):
            stats["classes"] += 1

    max_depth = max_loop_depth(tree)
    stats["max_loop_depth"] = max_depth
    if max_depth > MAX_LOOP_DEPTH:
        violations.append(
            f"Maximum loop nesting depth ({max_depth}) exceeds limit ({MAX_LOOP_DEPTH})"
        )

    return violations, stats


def cyclomatic_complexity(
    func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
) -> int:
    """Approximate McCabe cyclomatic complexity."""
    complexity = 1  # Base path
    branch_nodes = (
        ast.If,
        ast.For,
        ast.While,
        ast.ExceptHandler,
        ast.With,
        ast.Assert,
    )
    for node in ast.walk(func_node):
        if isinstance(node, branch_nodes):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
    return complexity


def max_loop_depth(tree: ast.AST) -> int:
    """Calculate maximum loop nesting depth via DFS."""
    result = 0
    loop_types = (ast.For, ast.While, ast.AsyncFor)

    def _walk(node: ast.AST, depth: int) -> None:
        nonlocal result
        for child in ast.iter_child_nodes(node):
            if isinstance(child, loop_types):
                new_depth = depth + 1
                if new_depth > result:
                    result = new_depth
                _walk(child, new_depth)
            else:
                _walk(child, depth)

    _walk(tree, 0)
    return result
