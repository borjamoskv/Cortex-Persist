"""
CORTEX v5.0 — MEJORAlo X-Ray Scanner.

Execute X-Ray 13D scan on a project directory.
Refactored: scan() orchestrates, helpers do collection + scoring + assembly.
"""

import ast
import logging
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from cortex.mejoralo.constants import (
    MAX_LOC,
    PSI_PATTERNS,
    SCAN_EXTENSIONS,
    SECURITY_PATTERNS,
    SKIP_DIRS,
)
from cortex.mejoralo.models import DimensionResult, ScanResult
from cortex.mejoralo.utils import detect_stack

__all__ = ["scan"]

logger = logging.getLogger("cortex.mejoralo")

_WEIGHT_MAP = {"critical": 40, "high": 35, "medium": 15, "low": 10}


# ─── File Collection ─────────────────────────────────────────────────


def _collect_source_files(root: Path, extensions: set[str]) -> list[Path]:
    """Walk directory and collect source files, skipping SKIP_DIRS."""
    source_files: list[Path] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            fp = Path(dirpath) / f
            if fp.suffix in extensions and f not in ("constants.py", "xray_scan.py"):
                source_files.append(fp)
    return source_files


# ─── Per-File Analysis ───────────────────────────────────────────────


_COMPLEXITY_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.AsyncFor,
    ast.And,
    ast.Or,
    ast.ExceptHandler,
    ast.With,
    ast.AsyncWith,
    ast.Try,
)

_NESTING_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncFor,
    ast.AsyncWith,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.ExceptHandler,
)


class McCabeVisitor(ast.NodeVisitor):
    def __init__(self, rel: str, findings: list[str]) -> None:
        self.complexity = 1  # Base complexity per function/module
        self.rel = rel
        self.findings = findings

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_complexity(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_complexity(node)

    def _check_complexity(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # Calculate McCabe for this scope
        comp = 1
        for child in ast.walk(node):
            if isinstance(child, _COMPLEXITY_NODES):
                comp += 1

        if comp > 10:  # Sovereign threshold: 10
            self.findings.append(
                f"{self.rel}:{node.lineno} -> High Complexity ({comp}) in '{node.name}'"
            )


class NestingVisitor(ast.NodeVisitor):
    def __init__(self, rel: str, findings: list[str]) -> None:
        self.depth = 0
        self.rel = rel
        self.findings = findings

    def visit(self, node: ast.AST) -> None:
        inc = isinstance(node, _NESTING_NODES)
        if inc:
            self.depth += 1
            if self.depth >= 6:  # Strict sovereign depth: 6
                line_no = getattr(node, "lineno", "?")
                self.findings.append(
                    f"{self.rel}:{line_no} -> Severe structural nesting (depth {self.depth})"
                )

        self.generic_visit(node)

        if inc:
            self.depth -= 1


def _analyze_python_complexity(content: str, rel: str) -> list[str]:
    findings: list[str] = []
    try:
        tree = ast.parse(content)
        McCabeVisitor(rel, findings).visit(tree)
        NestingVisitor(rel, findings).visit(tree)
    except SyntaxError:
        pass
    return findings


def _analyze_polyglot_nesting(lines: list[str], rel: str) -> list[str]:
    comp = []
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*", '"""', "'''", "]", "}", ")")):
            continue
        indent = len(line) - len(stripped)
        if indent >= 24 and any(
            stripped.startswith(kw)
            for kw in (
                "if ",
                "for ",
                "while ",
                "class ",
                "def ",
                "function ",
                "try",
                "catch",
                "else",
                "switch ",
                "with ",
            )
        ):
            comp.append(f"{rel}:{i} -> High nesting detected (indent {indent})")
    return comp


def _analyze_single_file(
    sf: Path, root: Path
) -> tuple[int, str | None, list[str], list[str], list[str]]:
    """Analyse a single file and return its metrics."""
    try:
        content = sf.read_text(errors="replace")
        lines = content.splitlines()
    except OSError:
        return 0, None, [], [], []

    loc = len(lines)
    rel = str(sf.relative_to(root))
    large_file = f"{rel} ({loc} LOC)" if loc > MAX_LOC else None

    # 130/100 Sovereign: McCabe + AST Structural Nesting for Python + Smart Polyglot
    if sf.suffix == ".py":
        comp = _analyze_python_complexity(content, rel)
    else:
        comp = _analyze_polyglot_nesting(lines, rel)

    psi = []
    sec = []
    for match in PSI_PATTERNS.finditer(content):
        line_no = content[: match.start()].count("\n") + 1
        psi.append(f"{rel}:{line_no} → {match.group()}")

    for match in SECURITY_PATTERNS.finditer(content):
        line_no = content[: match.start()].count("\n") + 1
        sec.append(f"{rel}:{line_no} → {match.group()}")

    return loc, large_file, psi, sec, comp


def _analyze_files(
    source_files: list[Path],
    root: Path,
) -> tuple[int, list[str], list[str], list[str], list[str]]:
    """Analyze all source files for LOC, architecture, psi, security, complexity.

    Returns:
        (total_loc, large_files, psi_findings, security_findings, complexity_findings)
    """
    total_loc = 0
    large_files: list[str] = []
    psi_findings: list[str] = []
    security_findings: list[str] = []
    complexity_findings: list[str] = []

    with ProcessPoolExecutor() as executor:
        # Parallel analysis of files
        results = executor.map(_analyze_single_file, source_files, [root] * len(source_files))

    for loc, large, psi, sec, comp in results:
        total_loc += loc
        if large:
            large_files.append(large)
        psi_findings.extend(psi)
        security_findings.extend(sec)
        complexity_findings.extend(comp)

    return total_loc, large_files, psi_findings, security_findings, complexity_findings


# ─── Dimension Scoring ───────────────────────────────────────────────


def _score_dimensions(
    source_files: list[Path],
    total_loc: int,
    large_files: list[str],
    psi_findings: list[str],
    security_findings: list[str],
    complexity_findings: list[str],
    brutal: bool = False,
) -> list[DimensionResult]:
    """Calculate scores for each X-Ray dimension."""
    dimensions: list[DimensionResult] = []
    has_files = bool(source_files)

    # 1. Integrity
    dimensions.append(
        DimensionResult(
            name="Integridad",
            score=100 if has_files else 0,
            weight="critical",
            findings=[] if has_files else ["No se encontraron archivos fuente"],
        )
    )

    # 2. Architecture
    if not has_files:
        arch_score = 0
    else:
        ratio_ok = 1 - (len(large_files) / len(source_files))
        arch_score = max(0, min(100, int(ratio_ok * 100)))
    dimensions.append(
        DimensionResult(
            name="Arquitectura",
            score=arch_score,
            weight="critical",
            findings=large_files[:10],
        )
    )

    # 3. Security
    if not has_files:
        sec_score = 0
    else:
        sec_score = max(0, 100 - min(100, len(security_findings) * 15))
    dimensions.append(
        DimensionResult(
            name="Seguridad",
            score=sec_score,
            weight="critical",
            findings=security_findings[:10],
        )
    )

    # 4. Complexity
    if not has_files:
        complexity_score = 0
    else:
        complexity_ratio = len(complexity_findings) / max(1, total_loc)
        penalty = min(100, int(complexity_ratio * 100))
        complexity_score = max(0, 100 - penalty)
    dimensions.append(
        DimensionResult(
            name="Complejidad",
            score=complexity_score,
            weight="high",
            findings=complexity_findings[:15],
        )
    )

    # 13. Psi
    if not has_files:
        psi_score = 0
    else:
        psi_penalty_base = 5 if not brutal else 10
        psi_score = max(0, 100 - min(100, len(psi_findings) * psi_penalty_base))

    dimensions.append(
        DimensionResult(
            name="Psi",
            score=psi_score,
            weight="high",
            findings=psi_findings[:15],
        )
    )

    # 14. Sovereign Excellence (Sovereign Pass)
    # Provides up to 30 bonus points for perfect code.
    sov_score = 0
    sov_findings = []
    if (
        has_files
        and arch_score == 100
        and sec_score == 100
        and complexity_score == 100
        and psi_score == 100
    ):
        sov_score = 100
        sov_findings = ["Sovereign Quality Standard achieved (130/100)"]

    dimensions.append(
        DimensionResult(
            name="Excelencia Soberana",
            score=sov_score,
            weight="sovereign",
            findings=sov_findings,
        )
    )

    return dimensions


def _compute_weighted_score(dimensions: list[DimensionResult]) -> int:
    """Calculate weighted total score from dimensions. Supports >100 for Sovereign standard."""
    _LOCAL_WEIGHT_MAP = {
        "critical": 40,
        "high": 35,
        "medium": 15,
        "low": 10,
        "sovereign": 30,  # Bonus weight
    }
    total_weight = 0
    weighted_sum = 0
    bonus_points = 0

    for d in dimensions:
        if d.weight == "sovereign":
            bonus_points = int(d.score * 0.3)  # Max +30
            continue

        w = _LOCAL_WEIGHT_MAP.get(d.weight, 10)
        weighted_sum += d.score * w
        total_weight += w

    base_score = int(weighted_sum / total_weight) if total_weight > 0 else 0
    return base_score + bonus_points


# ─── Main Entry Point ────────────────────────────────────────────────


def scan(project: str, path: str | Path, deep: bool = False, brutal: bool = False) -> ScanResult:
    """Execute X-Ray 13D scan on a project directory.

    If brutal is True, deep is implied and penalties are more severe.

    Dimensions analysed:
      CRITICAL (weight 40): Integrity, Architecture, Security
      HIGH (weight 35): Psi (toxic markers), Complexity
    """
    root = Path(path).resolve()
    if root.is_file():
        # Single file scan mode
        source_files = [root]
        root_dir = root.parent
    elif root.is_dir():
        # Directory scan mode
        root_dir = root
    else:
        raise ValueError(f"Path is not a directory or file: {root}")

    stack = detect_stack(root_dir)
    exts = SCAN_EXTENSIONS.get(stack, SCAN_EXTENSIONS["unknown"])

    if root.is_dir():
        source_files = _collect_source_files(root_dir, exts)

    total_loc, large_files, psi, sec, comp = _analyze_files(source_files, root_dir)

    dimensions = _score_dimensions(
        source_files,
        total_loc,
        large_files,
        psi,
        sec,
        comp,
        brutal=brutal,
    )
    score = _compute_weighted_score(dimensions)

    return ScanResult(
        project=project,
        score=score,
        dimensions=dimensions,
        total_files=len(source_files),
        total_loc=total_loc,
        stack=stack,
        dead_code=(len(source_files) == 0),
        brutal=brutal,
    )
