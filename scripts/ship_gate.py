#!/usr/bin/env python3
"""CORTEX Ship Gate — Blocks deploy if quality checks fail.

Exit 0 = safe to ship. Exit 1 = blocked.
Outputs a JSON report to stdout.

Usage:
    python scripts/ship_gate.py              # all checks
    python scripts/ship_gate.py --fast       # skip slow tests
    python scripts/ship_gate.py --json-only  # suppress Rich output
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

# ── Thresholds ──────────────────────────────────────────────────────

MAX_CC: Final[int] = 25  # Cyclomatic Complexity ceiling
MIN_MEJORALO: Final[int] = 50  # MEJORAlo minimum score
RUFF_TARGET: Final[str] = "cortex/ tests/"
PYTEST_TIMEOUT: Final[int] = 120  # seconds


@dataclass(slots=True)
class CheckResult:
    """Result of a single quality check."""

    name: str
    passed: bool
    status: str = ""
    duration_ms: float = 0.0
    detail: str = ""


@dataclass(slots=True)
class GateReport:
    """Full ship gate report."""

    gate: str = "UNKNOWN"
    timestamp: str = ""
    total_duration_ms: float = 0.0
    checks: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "gate": self.gate,
            "timestamp": self.timestamp,
            "total_duration_ms": round(self.total_duration_ms, 1),
            "checks": [asdict(c) for c in self.checks],
        }


def _run(cmd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a shell command and return result."""
    return subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=timeout,
    )


def _resolve_tool_command(binary_name: str, module_name: str) -> str | None:
    """Resolve a local venv binary first, then PATH, then `python -m module`."""
    local_binary = REPO_ROOT / ".venv" / "bin" / binary_name
    if local_binary.exists():
        return shlex.quote(str(local_binary))

    global_binary = shutil.which(binary_name)
    if global_binary:
        return shlex.quote(global_binary)

    probe = subprocess.run(
        [sys.executable, "-m", module_name, "--version"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return f"{shlex.quote(sys.executable)} -m {module_name}"
    return None


def check_ruff() -> CheckResult:
    """Lint check via ruff."""
    t0 = time.monotonic()
    ruff_cmd = _resolve_tool_command("ruff", "ruff")
    if not ruff_cmd:
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(
            name="ruff_lint",
            passed=False,
            status="failed",
            duration_ms=round(ms, 1),
            detail="ruff not available",
        )

    result = _run(f"{ruff_cmd} check {RUFF_TARGET}")
    ms = (time.monotonic() - t0) * 1000
    passed = result.returncode == 0
    error_count = len(result.stdout.strip().splitlines()) if not passed else 0
    return CheckResult(
        name="ruff_lint",
        passed=passed,
        status="ok" if passed else "failed",
        duration_ms=round(ms, 1),
        detail=f"{error_count} violations" if not passed else "clean",
    )


def check_tests(fast: bool = False) -> CheckResult:
    """Run pytest suite."""
    t0 = time.monotonic()
    pytest_cmd = _resolve_tool_command("pytest", "pytest")
    if not pytest_cmd:
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(
            name="pytest",
            passed=False,
            status="failed",
            duration_ms=round(ms, 1),
            detail="pytest not available",
        )

    marker = '-m "not slow"' if fast else ""
    result = _run(
        f"{pytest_cmd} tests/ {marker} --tb=line -q --no-header",
        timeout=PYTEST_TIMEOUT,
    )
    ms = (time.monotonic() - t0) * 1000

    # Parse summary line like "1162 passed, 3 warnings in 45.2s"
    lines = result.stdout.strip().splitlines()
    summary = lines[-1] if lines else ""
    passed = result.returncode == 0

    return CheckResult(
        name="pytest",
        passed=passed,
        status="ok" if passed else "failed",
        duration_ms=round(ms, 1),
        detail=summary if summary else result.stderr.strip()[:200],
    )


def check_radon_cc() -> CheckResult:
    """Scan cyclomatic complexity via radon."""
    t0 = time.monotonic()
    try:
        from radon.complexity import cc_visit
    except ImportError:
        return CheckResult(
            name="radon_cc",
            passed=False,
            status="skipped",
            duration_ms=0,
            detail="radon not installed, skipped",
        )

    worst_cc = 0
    worst_file = ""
    scanned = 0

    cortex_dir = REPO_ROOT / "cortex"
    for py_file in cortex_dir.rglob("*.py"):
        if any(p in py_file.parts for p in ("__pycache__", ".venv", "node_modules")):
            continue
        try:
            code = py_file.read_text(encoding="utf-8")
            blocks = cc_visit(code)
            for b in blocks:
                if b.complexity > worst_cc:
                    worst_cc = b.complexity
                    worst_file = str(py_file.relative_to(REPO_ROOT))
            scanned += 1
        except (SyntaxError, UnicodeDecodeError):
            continue

    ms = (time.monotonic() - t0) * 1000
    passed = worst_cc <= MAX_CC
    detail = f"scanned {scanned} files, max_cc={worst_cc}"
    if worst_file:
        detail += f" ({worst_file})"

    return CheckResult(
        name="radon_cc",
        passed=passed,
        status="ok" if passed else "failed",
        duration_ms=round(ms, 1),
        detail=detail,
    )


def check_mejoralo() -> CheckResult:
    """Check MEJORAlo score if available."""
    t0 = time.monotonic()
    try:
        result = _run(".venv/bin/python -m cortex.mejoralo scan --score-only cortex/", timeout=60)
        ms = (time.monotonic() - t0) * 1000
        try:
            score = int(result.stdout.strip().split()[-1])
        except (ValueError, IndexError):
            return CheckResult(
                name="mejoralo",
                passed=False,
                status="skipped",
                duration_ms=round(ms, 1),
                detail="could not parse score, skipped",
            )
        return CheckResult(
            name="mejoralo",
            passed=score >= MIN_MEJORALO,
            status="ok" if score >= MIN_MEJORALO else "failed",
            duration_ms=round(ms, 1),
            detail=f"score={score}/{MIN_MEJORALO} minimum",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(
            name="mejoralo",
            passed=False,
            status="skipped",
            duration_ms=round(ms, 1),
            detail="timeout or not available, skipped",
        )


def _init_console(json_only: bool):
    """Try to initialize Rich console, return None if json_only or unavailable."""
    if json_only:
        return None
    try:
        from rich.console import Console

        console = Console()
        console.print("\n[bold cyan]🚢 CORTEX Ship Gate[/bold cyan]\n")
        return console
    except ImportError:
        return None


def _print_check(console, label: str, result: CheckResult) -> None:
    """Print a single check result to console."""
    if console is None:
        return
    icon = "⚪" if result.status == "skipped" else ("✅" if result.passed else "❌")
    console.print(f"  {icon} {label}: {result.detail} ({result.duration_ms:.0f}ms)")


def _print_gate(console, report: GateReport) -> None:
    """Print final gate verdict."""
    if console is None:
        return
    console.print()
    if report.gate == "PASS":
        console.print("[bold green]🟢 GATE: PASS — Safe to ship.[/bold green]\n")
    elif report.gate == "DEGRADED":
        skipped = [c.name for c in report.checks if c.status == "skipped"]
        console.print(f"[bold yellow]🟡 GATE: DEGRADED — Missing or skipped checks: {', '.join(skipped)}[/bold yellow]\n")
    else:
        failed = [c.name for c in report.checks if c.status == "failed" or not c.passed]
        console.print(f"[bold red]🔴 GATE: FAIL — Blocked by: {', '.join(failed)}[/bold red]\n")


def main() -> None:
    fast = "--fast" in sys.argv
    json_only = "--json-only" in sys.argv
    console = _init_console(json_only)

    t0 = time.monotonic()
    report = GateReport(timestamp=datetime.now(timezone.utc).isoformat())

    checks = [
        ("Lint", check_ruff),
        ("Tests", lambda: check_tests(fast=fast)),
        ("Complexity", check_radon_cc),
        ("Quality", check_mejoralo),
    ]

    for label, fn in checks:
        try:
            result = fn()
        except Exception as e:
            result = CheckResult(name=label.lower(), passed=False, detail=str(e))
        report.checks.append(result)
        _print_check(console, label, result)

    report.total_duration_ms = (time.monotonic() - t0) * 1000
    has_failed = any(c.status == "failed" or not c.passed for c in report.checks)
    has_skipped = any(c.status == "skipped" for c in report.checks)
    if has_failed:
        report.gate = "FAIL"
    elif has_skipped:
        report.gate = "DEGRADED"
    else:
        report.gate = "PASS"

    _print_gate(console, report)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    sys.exit(0 if report.gate == "PASS" else 1)


if __name__ == "__main__":
    main()
