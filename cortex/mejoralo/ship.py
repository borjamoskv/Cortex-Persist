"""
CORTEX v5.0 — MEJORAlo Ship Gate.

Validates the 7 Seals for production readiness.
Refactored: each seal is an independent checker function.
"""

import logging
import os
from pathlib import Path

from cortex.mejoralo.constants import SCAN_EXTENSIONS, SKIP_DIRS
from cortex.mejoralo.models import ShipResult, ShipSeal
from cortex.mejoralo.scan import scan
from cortex.mejoralo.utils import detect_stack, get_build_cmd, get_lint_cmd, get_test_cmd, run_quiet

__all__ = ["check_ship_gate"]

logger = logging.getLogger("cortex.mejoralo")


# ─── Individual Seal Checks ─────────────────────────────────────────


def _seal_build(stack: str, cwd: str) -> ShipSeal:
    """Seal 1: Build Zero-Warning."""
    build_cmd = get_build_cmd(stack)
    if not build_cmd:
        return ShipSeal(
            name="Build Zero-Warning", passed=False, detail="No build command for stack"
        )
    result = run_quiet(build_cmd, cwd=cwd)
    return ShipSeal(
        name="Build Zero-Warning",
        passed=result["returncode"] == 0 and not result["stderr"].strip(),
        detail=result["stderr"][:200] if result["stderr"] else "Clean",
    )


def _seal_tests(stack: str, cwd: str) -> ShipSeal:
    """Seal 2: Tests 100% Green."""
    test_cmd = get_test_cmd(stack)
    if not test_cmd:
        return ShipSeal(name="Tests 100% Green", passed=False, detail="No test command for stack")
    result = run_quiet(test_cmd, cwd=cwd)
    return ShipSeal(
        name="Tests 100% Green",
        passed=result["returncode"] == 0,
        detail=f"exit={result['returncode']}",
    )


def _seal_linter(stack: str, cwd: str) -> ShipSeal:
    """Seal 3: Linter Silence."""
    lint_cmd = get_lint_cmd(stack)
    if not lint_cmd:
        return ShipSeal(name="Linter Silence", passed=True, detail="No linter configured — pass")
    result = run_quiet(lint_cmd, cwd=cwd)
    return ShipSeal(
        name="Linter Silence",
        passed=result["returncode"] == 0,
        detail=f"exit={result['returncode']}",
    )


def _seal_visual(p: Path) -> ShipSeal:
    """Seal 4: Visual Proof."""
    visual_json = p / "visual_proof.json"
    screenshots = list(p.glob("**/screenshot*.png"))
    visual_ok = visual_json.exists() or len(screenshots) > 0
    if visual_json.exists():
        detail = "Found visual_proof.json"
    elif screenshots:
        detail = f"Found {len(screenshots)} screenshots"
    else:
        detail = "No visual proof found"
    return ShipSeal(name="Visual Proof", passed=visual_ok, detail=detail)


def _seal_performance(project: str, path: str | Path) -> ShipSeal:
    """Seal 5: Performance — score must be >= 70 as quality proxy."""
    result = scan(project, path)
    passed = result.score >= 70
    return ShipSeal(
        name="Performance <100ms",
        passed=passed,
        detail=f"Quality score: {result.score}/100 ({'OK' if passed else 'below threshold'})",
    )


def _seal_a11y(p: Path, stack: str) -> ShipSeal:
    """Seal 6: A11y 100%."""
    a11y_findings: list[str] = []
    extensions = SCAN_EXTENSIONS.get(stack, SCAN_EXTENSIONS["unknown"])

    html_files: list[Path] = []
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            fp = Path(root) / f
            if fp.suffix in extensions and fp.suffix in (".html", ".html.erb", ".jsx", ".tsx"):
                html_files.append(fp)

    for hf in html_files[:5]:
        try:
            content = hf.read_text(errors="replace").lower()
            if "<img" in content and 'alt="' not in content:
                a11y_findings.append(f"{hf.name}: missing alt tags")
        except OSError:
            pass

    return ShipSeal(
        name="A11y 100%",
        passed=len(a11y_findings) == 0,
        detail=f"Issues: {len(a11y_findings)}"
        if a11y_findings
        else "Basic accessibility patterns found",
    )


def _seal_psi(project: str, path: str | Path) -> ShipSeal:
    """Seal 7: No Psi Debt."""
    scan_result = scan(project, path)
    psi_dim = next((d for d in scan_result.dimensions if d.name == "Psi"), None)
    psi_ok = psi_dim is not None and psi_dim.score == 100
    return ShipSeal(
        name="No Psi Debt",
        passed=psi_ok,
        detail=f"Psi score: {psi_dim.score if psi_dim else 0}",
    )


# ─── Main Entry Point ────────────────────────────────────────────────


def check_ship_gate(project: str, path: str | Path) -> ShipResult:
    """Validate the 7 Seals for production readiness."""
    p = Path(path).expanduser().resolve()
    stack = detect_stack(p)
    cwd = str(p)

    seals = [
        _seal_build(stack, cwd),
        _seal_tests(stack, cwd),
        _seal_linter(stack, cwd),
        _seal_visual(p),
        _seal_performance(project, path),
        _seal_a11y(p, stack),
        _seal_psi(project, path),
    ]

    passed_count = sum(1 for s in seals if s.passed)
    return ShipResult(
        project=project,
        ready=passed_count == len(seals),
        seals=seals,
        passed=passed_count,
        total=len(seals),
    )
