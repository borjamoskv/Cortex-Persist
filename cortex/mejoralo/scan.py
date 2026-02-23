"""
CORTEX v4.3 — MEJORAlo X-Ray Scanner.

Execute X-Ray 13D scan on a project directory.
Refactored: scan() orchestrates, helpers do collection + scoring + assembly.
"""

import logging
import os
from pathlib import Path

from cortex.mejoralo.constants import (
    MAX_LOC,
    PSI_PATTERNS,
    SCAN_EXTENSIONS,
    SECURITY_PATTERNS,
    SKIP_DIRS,
)
from cortex.mejoralo.types import DimensionResult, ScanResult
from cortex.mejoralo.utils import detect_stack

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


def _analyze_files(
    source_files: list[Path],
    root: Path,
) -> tuple[int, list[str], list[str], list[str], int]:
    """Analyze all source files for LOC, architecture, psi, security, complexity.

    Returns:
        (total_loc, large_files, psi_findings, security_findings, complexity_penalties)
    """
    total_loc = 0
    large_files: list[str] = []
    psi_findings: list[str] = []
    security_findings: list[str] = []
    complexity_penalties = 0

    for sf in source_files:
        try:
            lines = sf.read_text(errors="replace").splitlines()
        except OSError:
            continue

        loc = len(lines)
        total_loc += loc
        rel = str(sf.relative_to(root))

        if loc > MAX_LOC:
            large_files.append(f"{rel} ({loc} LOC)")

        for line in lines:
            indent = len(line) - len(line.lstrip())
            if indent >= 16:
                complexity_penalties += 1

        content = "\n".join(lines)

        for match in PSI_PATTERNS.finditer(content):
            line_no = content[: match.start()].count("\n") + 1
            psi_findings.append(f"{rel}:{line_no} → {match.group()}")

        for match in SECURITY_PATTERNS.finditer(content):
            line_no = content[: match.start()].count("\n") + 1
            security_findings.append(f"{rel}:{line_no} → {match.group()}")

    return total_loc, large_files, psi_findings, security_findings, complexity_penalties


# ─── Dimension Scoring ───────────────────────────────────────────────


def _score_dimensions(
    source_files: list[Path],
    total_loc: int,
    large_files: list[str],
    psi_findings: list[str],
    security_findings: list[str],
    complexity_penalties: int,
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
        penalty = 0
    else:
        complexity_ratio = complexity_penalties / max(1, total_loc)
        penalty = min(100, int(complexity_ratio * 100))
        complexity_score = max(0, 100 - penalty)
    dimensions.append(
        DimensionResult(
            name="Complejidad",
            score=complexity_score,
            weight="high",
            findings=(
                [f"High nesting detected in {len(source_files)} files"] if penalty > 0 else []
            ),
        )
    )

    # 13. Psi
    if not has_files:
        psi_score = 0
    else:
        psi_score = max(0, 100 - min(100, len(psi_findings) * 5))
    dimensions.append(
        DimensionResult(
            name="Psi",
            score=psi_score,
            weight="high",
            findings=psi_findings[:15],
        )
    )

    return dimensions


def _compute_weighted_score(dimensions: list[DimensionResult]) -> int:
    """Calculate weighted total score from dimensions."""
    total_weight = 0
    weighted_sum = 0
    for d in dimensions:
        w = _WEIGHT_MAP.get(d.weight, 10)
        weighted_sum += d.score * w
        total_weight += w
    return int(weighted_sum / total_weight) if total_weight > 0 else 0


# ─── Main Entry Point ────────────────────────────────────────────────


def scan(project: str, path: str | Path, deep: bool = False) -> ScanResult:
    """Execute X-Ray 13D scan on a project directory.

    Dimensions analysed:
      CRITICAL (weight 40): Integrity, Architecture, Security
      HIGH (weight 35): Psi (toxic markers), Complexity
    """
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(f"Path is not a directory: {p}")

    stack = detect_stack(p)
    extensions = SCAN_EXTENSIONS.get(stack, SCAN_EXTENSIONS["unknown"])

    source_files = _collect_source_files(p, extensions)
    analysis = _analyze_files(source_files, p)
    total_loc, large_files, psi_findings, security_findings, complexity_penalties = analysis

    dimensions = _score_dimensions(
        source_files,
        total_loc,
        large_files,
        psi_findings,
        security_findings,
        complexity_penalties,
    )
    final_score = _compute_weighted_score(dimensions)

    return ScanResult(
        project=project,
        stack=stack,
        score=final_score,
        dimensions=dimensions,
        dead_code=final_score < 50,
        total_files=len(source_files),
        total_loc=total_loc,
    )
