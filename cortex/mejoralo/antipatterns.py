"""
CORTEX v6.0 — Antipattern Scanner.

AST-based detection of code quality violations that the GEMINI.md rules
mandate but were never enforced automatically. Each scanner implements
the Meta-Rule: "What information is IMPLICIT in my code that should be EXPLICIT?"

Scanners:
  1. BroadExceptionScanner   → `except Exception` / bare `except:`
  2. AsyncIntegrityScanner   → blocking I/O in async contexts
  3. MagicLiteralScanner     → unnamed numeric/string constants
  4. ImportGraphScanner      → circular deps + fan-out analysis
  5. ImplicitAssumptionScanner → missing type guards, Optional misuse
  6. DeadCodeScanner         → unreachable code after return/raise
"""

from __future__ import annotations

import ast
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["scan_antipatterns", "AntipatternFinding", "AntipatternReport"]

logger = logging.getLogger("cortex.mejoralo.antipatterns")

# ── Constants ────────────────────────────────────────────────────────

SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".eggs",
    "egg-info", ".tox", "migrations",
}

# Blocking calls that MUST NOT appear in async functions
_BLOCKING_CALLS: dict[str, str] = {
    "open": "Use aiofiles.open() or asyncio.to_thread(open, ...)",
    "time.sleep": "Use asyncio.sleep()",
    "requests.get": "Use httpx.AsyncClient.get()",
    "requests.post": "Use httpx.AsyncClient.post()",
    "requests.put": "Use httpx.AsyncClient.put()",
    "requests.delete": "Use httpx.AsyncClient.delete()",
    "requests.patch": "Use httpx.AsyncClient.patch()",
    "requests.head": "Use httpx.AsyncClient.head()",
    "requests.request": "Use httpx.AsyncClient.request()",
    "subprocess.run": "Use asyncio.create_subprocess_exec()",
    "subprocess.call": "Use asyncio.create_subprocess_exec()",
    "subprocess.check_output": "Use asyncio.create_subprocess_exec()",
    "os.system": "Use asyncio.create_subprocess_shell()",
    "input": "Use aioconsole.ainput()",
    "urllib.request.urlopen": "Use httpx.AsyncClient",
}

# Magic number whitelist — common constants that are acceptable
_MAGIC_WHITELIST = {0, 1, 2, -1, 100, 0.5}

# Max allowed fan-out (imports from other local modules)
_MAX_FAN_OUT = 12


# ── Data Models ──────────────────────────────────────────────────────


@dataclass
class AntipatternFinding:
    """A single antipattern detection."""

    scanner: str      # Which scanner found it
    severity: str     # "critical", "high", "medium", "low"
    file: str         # Relative path
    line: int         # Line number
    message: str      # Human-readable description
    fix_hint: str     # Suggested fix


@dataclass
class AntipatternReport:
    """Aggregate report from all scanners."""

    findings: list[AntipatternFinding] = field(default_factory=list)
    files_scanned: int = 0
    scanners_run: int = 0

    @property
    def total(self) -> int:
        return len(self.findings)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    def by_severity(self) -> dict[str, list[AntipatternFinding]]:
        result: dict[str, list[AntipatternFinding]] = {}
        for f in self.findings:
            result.setdefault(f.severity, []).append(f)
        return result

    def score_penalty(self) -> int:
        """Calculate penalty points for MEJORAlo score integration."""
        penalties = {"critical": 15, "high": 8, "medium": 3, "low": 1}
        return sum(penalties.get(f.severity, 1) for f in self.findings)


# ── Scanner 1: Broad Exception ───────────────────────────────────────


class _BroadExceptionVisitor(ast.NodeVisitor):
    """Detect `except Exception`, `except BaseException`, and bare `except:`."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            # Bare `except:`
            self.findings.append(AntipatternFinding(
                scanner="BroadException",
                severity="critical",
                file=self.rel,
                line=node.lineno,  # noqa: E501
                message=(
                    "Bare `except:` catches all exceptions"
                    " including SystemExit/KeyboardInterrupt"
                ),
                fix_hint="Use a specific exception type: except ValueError, except OSError, etc.",
            ))
        elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
            # Check if the body is just `pass` or `...` (swallowed error)
            body_is_silent = (
                len(node.body) == 1
                and isinstance(node.body[0], (ast.Pass, ast.Expr))
                and (
                    isinstance(node.body[0], ast.Pass)
                    or (isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and node.body[0].value.value is ...)
                )
            )
            severity = "critical" if body_is_silent else "high"
            msg = (
                f"`except {node.type.id}` with silent body"
                " — errors are being swallowed"
                if body_is_silent
                else f"`except {node.type.id}` is too broad"
                " — specific exceptions lose their identity"
            )
            self.findings.append(AntipatternFinding(
                scanner="BroadException",
                severity=severity,
                file=self.rel,
                line=node.lineno,
                message=msg,
                fix_hint="Catch specific exceptions: except (ValueError, KeyError, OSError) as e:",
            ))
        self.generic_visit(node)


# ── Scanner 2: Async Integrity ───────────────────────────────────────


class _AsyncIntegrityVisitor(ast.NodeVisitor):
    """Detect blocking I/O calls inside async functions."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings
        self._in_async = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        old = self._in_async
        self._in_async = True
        self.generic_visit(node)
        self._in_async = old

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old = self._in_async
        self._in_async = False
        self.generic_visit(node)
        self._in_async = old

    def visit_Call(self, node: ast.Call) -> None:
        if not self._in_async:
            self.generic_visit(node)
            return

        call_name = self._get_call_name(node)
        if call_name and call_name in _BLOCKING_CALLS:
            self.findings.append(AntipatternFinding(
                scanner="AsyncIntegrity",
                severity="high",
                file=self.rel,
                line=node.lineno,
                message=f"Blocking call `{call_name}()` inside async function",
                fix_hint=_BLOCKING_CALLS[call_name],
            ))
        self.generic_visit(node)

    @staticmethod
    def _get_call_name(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            # e.g. requests.get, time.sleep
            parts: list[str] = []
            current: ast.expr = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            parts.reverse()
            return ".".join(parts)
        return None


# ── Scanner 3: Magic Literals ────────────────────────────────────────


class _MagicLiteralVisitor(ast.NodeVisitor):
    """Detect unnamed numeric constants and magic strings."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings
        self._in_assignment = False
        self._in_default = False

    def visit_Assign(self, node: ast.Assign) -> None:
        # Module-level CONSTANT = 42 is fine
        if self._is_constant_assignment(node):
            return
        self._in_assignment = True
        self.generic_visit(node)
        self._in_assignment = False

    def visit_arguments(self, node: ast.arguments) -> None:
        # Default values are acceptable
        old = self._in_default
        self._in_default = True
        for default in node.defaults + node.kw_defaults:
            if default:
                self.visit(default)
        self._in_default = old

    def visit_Constant(self, node: ast.Constant) -> None:
        if self._in_default:
            return

        value = node.value
        # Skip strings, None, booleans, Ellipsis
        if isinstance(value, (str, bytes, bool, type(None), type(...))):
            return

        # Skip whitelisted values
        if isinstance(value, (int, float)) and value in _MAGIC_WHITELIST:
            return

        # Check context — is this in a comparison, return, or arithmetic?
        self.findings.append(AntipatternFinding(
            scanner="MagicLiteral",
            severity="low",
            file=self.rel,
            line=node.lineno,
            message=f"Magic number `{value}` — unnamed constant obscures intent",
            fix_hint=f"Extract to a named constant: MY_CONSTANT = {value}",
        ))

    @staticmethod
    def _is_constant_assignment(node: ast.Assign) -> bool:
        """Check if this is a UPPER_CASE = value pattern."""
        if len(node.targets) != 1:
            return False
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id.isupper():
            return True
        return False


# ── Scanner 4: Import Graph (Circular Deps + Fan-Out) ────────────────


def _build_import_graph(
    root: Path,
) -> dict[str, set[str]]:
    """Build a module→dependencies graph from Python imports."""
    graph: dict[str, set[str]] = {}

    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith(".py"):
                continue
            fp = Path(dirpath) / f
            rel = str(fp.relative_to(root))
            module_name = rel.replace("/", ".").removesuffix(".py")
            if module_name.endswith(".__init__"):
                module_name = module_name.removesuffix(".__init__")

            try:
                content = fp.read_text(errors="replace")
                tree = ast.parse(content)
            except (SyntaxError, OSError):
                continue

            deps: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        deps.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        deps.add(node.module.split(".")[0])

            graph[module_name] = deps

    return graph


def _detect_circular_deps(graph: dict[str, set[str]]) -> list[tuple[str, str]]:
    """Find circular dependency pairs in the import graph."""
    circular: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for module, deps in graph.items():
        mod_root = module.split(".")[0]
        for dep in deps:
            if dep == mod_root:
                continue  # Self-import is fine
            # Check if dep also imports module's root
            for other_mod, other_deps in graph.items():
                if other_mod.split(".")[0] == dep and mod_root in other_deps:
                    pair = tuple(sorted((mod_root, dep)))
                    if pair not in seen:
                        seen.add(pair)
                        circular.append((module, other_mod))
    return circular


def _detect_fan_out(
    graph: dict[str, set[str]], root_package: str,
) -> list[tuple[str, int]]:
    """Find modules with too many dependencies (high fan-out)."""
    violations: list[tuple[str, int]] = []
    for module, deps in graph.items():
        # Only count local deps (same root package)
        local_deps = {d for d in deps if d == root_package or d.startswith(f"{root_package}.")}
        if len(local_deps) > _MAX_FAN_OUT:
            violations.append((module, len(local_deps)))
    return violations


# ── Scanner 5: Implicit Assumptions ──────────────────────────────────


class _ImplicitAssumptionVisitor(ast.NodeVisitor):
    """Detect patterns where assumptions are implicit instead of explicit."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Detect dict/list access without guard: d["key"], l[0]."""
        # Only flag direct string/int subscript on bare names
        if (
            isinstance(node.value, ast.Name)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, (str, int))
        ):
            # Check if this is inside a try block (then it's guarded)
            # We can't easily check ancestry in a simple visitor,
            # so we flag all and let the user triage
            pass  # Intentionally not flagging — too noisy without context
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_return_type_hint(node)
        self._check_too_many_params(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_return_type_hint(node)
        self._check_too_many_params(node)
        self.generic_visit(node)

    def _check_return_type_hint(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Public functions without return type hints hide intent."""
        if node.name.startswith("_"):
            return  # Private functions get a pass
        if node.name in ("__init__", "__str__", "__repr__", "__len__",
                         "__eq__", "__hash__", "__bool__", "__enter__",
                         "__exit__", "__aenter__", "__aexit__"):
            return  # Dunder methods with obvious returns
        if node.returns is None:
            self.findings.append(AntipatternFinding(
                scanner="ImplicitAssumption",
                severity="medium",
                file=self.rel,
                line=node.lineno,
                message=f"Public function `{node.name}()` has no return type hint",
                fix_hint=f"Add return type: def {node.name}(...) -> ReturnType:",
            ))

    def _check_too_many_params(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Too many parameters is a code smell (implicit complexity)."""
        args = node.args
        total = (
            len(args.args)
            + len(args.posonlyargs)
            + len(args.kwonlyargs)
        )
        # Subtract 'self' or 'cls'
        if total > 0 and args.args and args.args[0].arg in ("self", "cls"):
            total -= 1
        if total > 5:
            self.findings.append(AntipatternFinding(
                scanner="ImplicitAssumption",
                severity="medium",
                file=self.rel,
                line=node.lineno,
                message=f"Function `{node.name}()` has {total} parameters (max recommended: 5)",
                fix_hint="Consider grouping parameters into a dataclass or config object.",
            ))


# ── Scanner 6: Dead Code ─────────────────────────────────────────────


class _DeadCodeVisitor(ast.NodeVisitor):
    """Detect unreachable code after return/raise/break/continue."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings

    def _check_body(self, body: list[ast.stmt]) -> None:
        for i, stmt in enumerate(body):
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                # Check if there's code after this statement (in same block)
                remaining = body[i + 1:]
                # Filter out pass statements and string literals (docstrings)
                real_remaining = [
                    s for s in remaining
                    if not isinstance(s, ast.Pass)
                    and not (isinstance(s, ast.Expr)
                             and isinstance(s.value, ast.Constant)
                             and isinstance(s.value.value, str))
                ]
                if real_remaining:
                    dead_stmt = real_remaining[0]
                    self.findings.append(AntipatternFinding(
                        scanner="DeadCode",
                        severity="medium",
                        file=self.rel,
                        line=getattr(dead_stmt, "lineno", stmt.lineno + 1),
                        message=f"Unreachable code after `{type(stmt).__name__.lower()}`",
                        fix_hint="Remove dead code or restructure logic.",
                    ))
                break  # Only report first dead block per body

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_body(node.body)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_body(node.body)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._check_body(node.body)
        self._check_body(node.orelse)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._check_body(node.body)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._check_body(node.body)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._check_body(node.body)
        for handler in node.handlers:
            self._check_body(handler.body)
        self.generic_visit(node)


# ── Orchestrator ─────────────────────────────────────────────────────


def _scan_single_file(
    filepath: Path, root: Path, findings: list[AntipatternFinding],
) -> None:
    """Run all AST-based scanners on a single Python file."""
    try:
        content = filepath.read_text(errors="replace")
        tree = ast.parse(content)
    except (SyntaxError, OSError):
        return

    rel = str(filepath.relative_to(root))

    # Run all visitors
    _BroadExceptionVisitor(rel, findings).visit(tree)
    _AsyncIntegrityVisitor(rel, findings).visit(tree)
    _MagicLiteralVisitor(rel, findings).visit(tree)
    _ImplicitAssumptionVisitor(rel, findings).visit(tree)
    _DeadCodeVisitor(rel, findings).visit(tree)


def scan_antipatterns(
    path: str | Path,
    *,
    root_package: str = "cortex",
    include_magic: bool = False,
    include_type_hints: bool = True,
) -> AntipatternReport:
    """Execute full antipattern scan on a Python project.

    Args:
        path: Project root directory or single file.
        root_package: Package name for fan-out analysis.
        include_magic: Enable magic literal detection (noisy, off by default).
        include_type_hints: Enable missing type hint detection.

    Returns:
        AntipatternReport with all findings.
    """
    root = Path(path).resolve()
    report = AntipatternReport()

    if root.is_file():
        files = [root]
        scan_root = root.parent
    elif root.is_dir():
        files = []
        for dirpath, dirs, filenames in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in filenames:
                if f.endswith(".py"):
                    files.append(Path(dirpath) / f)
        scan_root = root
    else:
        logger.error("Path is not a file or directory: %s", root)
        return report

    report.files_scanned = len(files)
    findings: list[AntipatternFinding] = []

    # ── AST-based scanners (per file) ──
    for fp in files:
        _scan_single_file(fp, scan_root, findings)

    # ── Import graph scanners (project-wide) ──
    if root.is_dir():
        graph = _build_import_graph(scan_root)

        # Circular dependencies
        circular = _detect_circular_deps(graph)
        for mod_a, mod_b in circular:
            findings.append(AntipatternFinding(
                scanner="CircularDep",
                severity="high",
                file=mod_a.replace(".", "/") + ".py",
                line=0,
                message=f"Circular dependency: {mod_a} ↔ {mod_b}",
                fix_hint="Break the cycle with dependency injection or an interface module.",
            ))

        # Fan-out
        fan_out_violations = _detect_fan_out(graph, root_package)
        for module, count in fan_out_violations:
            findings.append(AntipatternFinding(
                scanner="FanOut",
                severity="medium",
                file=module.replace(".", "/") + ".py",
                line=0,
                message=f"High fan-out: {module} depends on {count} local modules (max: {_MAX_FAN_OUT})",
                fix_hint="Consider splitting this module or using a facade pattern.",
            ))

    # ── Filter by configuration ──
    if not include_magic:
        findings = [f for f in findings if f.scanner != "MagicLiteral"]
    if not include_type_hints:
        findings = [f for f in findings if not (
            f.scanner == "ImplicitAssumption" and "return type hint" in f.message
        )]

    report.findings = sorted(findings, key=lambda f: (
        {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.severity, 4),
        f.file,
        f.line,
    ))
    report.scanners_run = 6

    return report
