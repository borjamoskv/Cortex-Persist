"""sovereign_scorer_dimensions — Semantic and Test Coverage scorers.

Extracted from sovereign_scorer.py to satisfy the Landauer LOC barrier (≤500).
Contains: score_semantics (Dimension 2), score_tests (Dimension 4).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.moltbook.skills.sovereign_code_scorer.scripts.sovereign_scorer import Issue

__all__ = ["score_semantics", "score_tests"]


def score_semantics(files: list[Path]) -> tuple[float, list]:
    """Check naming, dead code, unused imports — Dimension 2 (25 pts)."""
    if not files:
        return 0.0, []

    from cortex.moltbook.skills.sovereign_code_scorer.scripts.sovereign_scorer import Issue

    issues: list[Issue] = []
    total_score = 25.0
    deductions = 0.0
    py_files = [f for f in files if f.suffix == ".py"]

    # Allowed single-char identifiers
    _ALLOWED_SHORT = {
        "i",
        "j",
        "k",
        "x",
        "y",
        "z",
        "_",
        "e",
        "f",
        "s",
        "c",
        "v",
        "n",
        "m",
        "t",
        "p",
        "d",
        "r",
    }

    for f in py_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        # Single-char variable names
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and len(node.id) == 1 and node.id not in _ALLOWED_SHORT:
                deductions += 0.2
                issues.append(
                    Issue(
                        file=str(f),
                        line=node.lineno,
                        category="semantics",
                        severity="info",
                        message=f"Single-char variable name '{node.id}'",
                    )
                )

        # Bare except
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                deductions += 1.0
                issues.append(
                    Issue(
                        file=str(f),
                        line=node.lineno,
                        category="semantics",
                        severity="warning",
                        message="Bare 'except:' — catch specific exceptions",
                    )
                )

        # Broad Exception catches
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type:
                if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    deductions += 0.5
                    issues.append(
                        Issue(
                            file=str(f),
                            line=node.lineno,
                            category="semantics",
                            severity="warning",
                            message="Broad 'except Exception' — use specific exception types",
                        )
                    )

        # Functions without docstrings
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                ):
                    if not node.name.startswith("_"):
                        deductions += 0.3
                        if len(issues) < 50:
                            issues.append(
                                Issue(
                                    file=str(f),
                                    line=node.lineno,
                                    category="semantics",
                                    severity="info",
                                    message=f"Function '{node.name}' lacks docstring",
                                )
                            )

    return max(0.0, total_score - deductions), issues


def score_tests(root: Path, files: list[Path]) -> tuple[float, list]:
    """Check test file existence and quality — Dimension 4 (20 pts)."""
    if not files:
        return 0.0, []

    from cortex.moltbook.skills.sovereign_code_scorer.scripts.sovereign_scorer import Issue

    issues: list[Issue] = []
    total_score = 20.0

    test_files = [f for f in files if "test" in f.name.lower() or f.parent.name == "tests"]
    source_files = [f for f in files if f not in test_files]

    if not source_files:
        return total_score, issues

    test_ratio = len(test_files) / len(source_files) if source_files else 0

    if test_ratio == 0:
        issues.append(
            Issue(
                file="project",
                line=0,
                category="tests",
                severity="critical",
                message="No test files found. Testing is not optional.",
            )
        )
        return 0.0, issues

    if test_ratio >= 0.8:
        ratio_score = 10.0
    elif test_ratio >= 0.5:
        ratio_score = 7.0
    elif test_ratio >= 0.3:
        ratio_score = 5.0
    else:
        ratio_score = test_ratio * 10.0

    # Check test quality (assertions)
    assertion_count = 0
    test_count = 0
    for tf in test_files:
        if tf.suffix != ".py":
            continue
        try:
            source = tf.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    if node.name.startswith("test_"):
                        test_count += 1
                        for child in ast.walk(node):
                            if isinstance(child, ast.Assert):
                                assertion_count += 1
                            elif isinstance(child, ast.Call):
                                if isinstance(child.func, ast.Attribute):
                                    if child.func.attr.startswith("assert"):
                                        assertion_count += 1
        except (SyntaxError, UnicodeDecodeError):
            continue

    quality_score = min(10.0, (assertion_count / max(test_count, 1)) * 5.0)
    return min(total_score, ratio_score + quality_score), issues
