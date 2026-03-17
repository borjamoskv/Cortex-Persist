"""Sovereign Code Scorer — Automated code quality engine.

Evaluates codebases on 5 dimensions (PoQ-5 Protocol):
  1. Syntax Health (20pts)
  2. Semantic Correctness (25pts)
  3. Consistency (20pts)
  4. Test Coverage (20pts)
  5. Aesthetic Quality (15pts)

Zero dependencies beyond stdlib.
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path
from typing import NamedTuple, Union

# Dimensions 2 & 4 → sovereign_scorer_dimensions.py (Landauer LOC barrier)
from sovereign_scorer_dimensions import (  # noqa: E402
    score_semantics,
    score_tests,
)

# ── Data Types ─────────────────────────────────────────────────


class ScoreResult(NamedTuple):
    syntax: float
    semantics: float
    consistency: float
    tests: float
    aesthetics: float

    @property
    def total(self) -> float:
        return self.syntax + self.semantics + self.consistency + self.tests + self.aesthetics

    @property
    def verdict(self) -> str:
        t = self.total
        if t >= 90:
            return "🏆 SOVEREIGN"
        if t >= 70:
            return "🟢 SOLID"
        if t >= 50:
            return "🟡 STANDARD"
        if t >= 30:
            return "🟠 BRUTAL"
        return "🔴 REWRITE"


class Issue(NamedTuple):
    file: str
    line: int
    category: str
    severity: str  # critical, warning, info
    message: str


# ── File Discovery ─────────────────────────────────────────────

EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

IGNORE_DIRS = {
    "__pycache__",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".tox",
    "env",
    ".eggs",
}


def discover_files(root: Path) -> list[Path]:
    """Find all scoreable source files."""
    files: list[Path] = []
    if root.is_file():
        if root.suffix in EXTENSIONS:
            return [root]
        return []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix in EXTENSIONS:
                files.append(fpath)
    return sorted(files)


# ── Dimension 1: Syntax Health (20 pts) ───────────────────────


def score_syntax(files: list[Path]) -> tuple[float, list[Issue]]:
    """Check for syntax errors and basic formatting."""
    if not files:
        return 0.0, []

    issues: list[Issue] = []
    errors = 0
    warnings = 0
    total_files = len(files)

    for f in files:
        if f.suffix != ".py":
            continue  # Only Python AST parse for now
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            ast.parse(source, filename=str(f))
        except SyntaxError as e:
            errors += 1
            issues.append(
                Issue(
                    file=str(f),
                    line=e.lineno or 0,
                    category="syntax",
                    severity="critical",
                    message=f"SyntaxError: {e.msg}",
                )
            )

        # Check formatting
        lines = source.split("\n") if "source" in dir() else []
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                warnings += 1
                if warnings <= 5:
                    issues.append(
                        Issue(
                            file=str(f),
                            line=i,
                            category="syntax",
                            severity="info",
                            message=f"Line too long ({len(line)} > 120 chars)",
                        )
                    )
            if "\t" in line and "    " in line:
                issues.append(
                    Issue(
                        file=str(f),
                        line=i,
                        category="syntax",
                        severity="warning",
                        message="Mixed tabs and spaces",
                    )
                )

    if total_files == 0:
        return 20.0, issues

    error_ratio = errors / total_files
    score = 20.0 * (1.0 - error_ratio) - min(warnings * 0.1, 5.0)
    return max(0.0, min(20.0, score)), issues


# ── Dimension 3: Consistency (20 pts) ─────────────────────────


def score_consistency(files: list[Path]) -> tuple[float, list[Issue]]:
    """Check naming convention consistency."""
    if not files:
        return 0.0, []

    issues: list[Issue] = []
    total_score = 20.0
    deductions = 0.0

    naming_styles: dict[str, int] = {"snake_case": 0, "camelCase": 0, "PascalCase": 0}

    py_files = [f for f in files if f.suffix == ".py"]
    for f in py_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                if name.startswith("__") and name.endswith("__"):
                    continue  # dunder
                if "_" in name:
                    naming_styles["snake_case"] += 1
                elif name[0].isupper():
                    naming_styles["PascalCase"] += 1
                elif name[0].islower() and any(c.isupper() for c in name):
                    naming_styles["camelCase"] += 1
                else:
                    naming_styles["snake_case"] += 1

    # Penalize mixed styles
    used_styles = {k: v for k, v in naming_styles.items() if v > 0}
    if len(used_styles) > 1:
        total_names = sum(used_styles.values())
        dominant = max(used_styles.values())
        consistency_ratio = dominant / total_names if total_names > 0 else 1.0
        deductions += (1.0 - consistency_ratio) * 10.0
        if consistency_ratio < 0.8:
            issues.append(
                Issue(
                    file="project",
                    line=0,
                    category="consistency",
                    severity="warning",
                    message=f"Mixed naming styles: {used_styles}. Stick to one convention.",
                )
            )

    return max(0.0, total_score - deductions), issues


# ── Dimension 5: Aesthetic Quality (15 pts) ──────────────────


def score_aesthetics(files: list[Path]) -> tuple[float, list[Issue]]:
    """Check file structure, documentation, readability."""
    if not files:
        return 0.0, []

    issues: list[Issue] = []
    total_score = 15.0
    deductions = 0.0

    for f in files:
        if f.suffix != ".py":
            continue
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        lines = source.split("\n")

        # File too long
        if len(lines) > 500:
            deductions += 1.0
            issues.append(
                Issue(
                    file=str(f),
                    line=0,
                    category="aesthetics",
                    severity="warning",
                    message=f"File has {len(lines)} lines (>500). Consider splitting.",
                )
            )

        # No module docstring
        try:
            tree = ast.parse(source)
            if not (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
            ):
                deductions += 0.5
        except SyntaxError:
            pass

        for i, line in enumerate(lines, 1):
            for marker in ("TODO", "FIXME", "HACK", "XXX"):
                if marker in line:
                    deductions += 0.2
                    if len(issues) < 50:
                        issues.append(
                            Issue(
                                file=str(f),
                                line=i,
                                category="aesthetics",
                                severity="info",
                                message=f"Found {marker} comment — resolve or document.",
                            )
                        )

    return max(0.0, total_score - deductions), issues


# ── Main Scorer ────────────────────────────────────────────────


def score(path: Union[str, Path], detailed: bool = False) -> dict:
    """Score a file or directory. Returns full report."""
    root = Path(path).resolve()
    if not root.exists():
        return {"error": f"Path not found: {root}"}

    files = discover_files(root)
    if not files:
        return {"error": f"No scoreable files found in {root}"}

    all_issues: list[Issue] = []

    s1, i1 = score_syntax(files)
    all_issues.extend(i1)

    s2, i2 = score_semantics(files)
    all_issues.extend(i2)

    s3, i3 = score_consistency(files)
    all_issues.extend(i3)

    s4, i4 = score_tests(root, files)
    all_issues.extend(i4)

    s5, i5 = score_aesthetics(files)
    all_issues.extend(i5)

    result = ScoreResult(
        syntax=round(s1, 1),
        semantics=round(s2, 1),
        consistency=round(s3, 1),
        tests=round(s4, 1),
        aesthetics=round(s5, 1),
    )

    report = {
        "path": str(root),
        "files_analyzed": len(files),
        "total_score": round(result.total, 1),
        "verdict": result.verdict,
        "dimensions": {
            "syntax": {"score": result.syntax, "max": 20},
            "semantics": {"score": result.semantics, "max": 25},
            "consistency": {"score": result.consistency, "max": 20},
            "tests": {"score": result.tests, "max": 20},
            "aesthetics": {"score": result.aesthetics, "max": 15},
        },
        "issue_count": len(all_issues),
        "critical_issues": sum(1 for i in all_issues if i.severity == "critical"),
    }

    if detailed:
        report["issues"] = [
            {
                "file": i.file,
                "line": i.line,
                "category": i.category,
                "severity": i.severity,
                "message": i.message,
            }
            for i in all_issues[:100]
        ]
        report["files"] = [str(f) for f in files]

    return report


def print_report(report: dict) -> None:
    """Pretty-print a score report."""
    if "error" in report:
        print(f"❌ {report['error']}")
        return

    t = report["total_score"]
    v = report["verdict"]
    dims = report["dimensions"]

    def bar(score: float, mx: float) -> str:
        ratio = score / mx
        if ratio >= 0.8:
            return "🟢"
        if ratio >= 0.5:
            return "🟡"
        return "🔴"

    print()
    print("╔══════════════════════════════════════════╗")
    print(f"║  SOVEREIGN CODE SCORE: {t:5.1f}/100  {v:>10s}  ║")
    print("╠══════════════════════════════════════════╣")
    for name, d in dims.items():
        s, m = d["score"], d["max"]
        icon = bar(s, m)
        print(f"║  {name:14s} {s:5.1f}/{m:<3d}  {icon:>20s}  ║")
    print("╠══════════════════════════════════════════╣")
    print(
        f"║  Files: {report['files_analyzed']:>3d}  Issues: {report['issue_count']:>3d}  "
        f"Critical: {report['critical_issues']:>2d}     ║"
    )
    print("╚══════════════════════════════════════════╝")

    if "issues" in report:
        crit = [i for i in report["issues"] if i["severity"] == "critical"]
        warn = [i for i in report["issues"] if i["severity"] == "warning"]
        if crit:
            print("\n🔴 CRITICAL:")
            for i in crit[:10]:
                print(f"  {i['file']}:{i['line']} — {i['message']}")
        if warn:
            print("\n🟡 WARNINGS:")
            for i in warn[:10]:
                print(f"  {i['file']}:{i['line']} — {i['message']}")


# ── CLI ────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python sovereign_scorer.py <path> [--detailed] [--json]")
        sys.exit(1)

    path = sys.argv[1]
    detailed = "--detailed" in sys.argv
    as_json = "--json" in sys.argv

    report = score(path, detailed=detailed)

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
