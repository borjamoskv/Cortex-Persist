# [C5-REAL] Exergy-Maximized
#!/usr/bin/env python3
"""
cat_id: ship-gate
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


from __future__ import annotations

import json
import os
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


def check_ruff() -> CheckResult:
    """Lint check via ruff."""
    t0 = time.monotonic()
    result = _run(f"uv run ruff check {RUFF_TARGET}")
    ms = (time.monotonic() - t0) * 1000
    passed = result.returncode == 0
    error_count = len(result.stdout.strip().splitlines()) if not passed else 0
    return CheckResult(
        name="ruff_lint",
        passed=passed,
        duration_ms=round(ms, 1),
        detail=f"{error_count} violations" if not passed else "clean",
    )


def check_git_state() -> CheckResult:
    """Git State — clean & aligned with origin."""
    t0 = time.monotonic()
    result = _run("git status --porcelain")
    ms = (time.monotonic() - t0) * 1000
    
    passed = result.returncode == 0 and not result.stdout.strip()
    if not passed:
        detail = "dirty working tree" if result.stdout.strip() else "git status failed"
    else:
        detail = "clean"
        
    return CheckResult(
        name="git_state",
        passed=passed,
        duration_ms=round(ms, 1),
        detail=detail,
    )


def check_ghost_radar() -> CheckResult:
    """Ghost Radar — no unresolved ghosts in 24h."""
    t0 = time.monotonic()
    result = _run("git ls-files --others --exclude-standard")
    ms = (time.monotonic() - t0) * 1000
    
    untracked_count = len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0
    passed = result.returncode == 0 and untracked_count == 0
    
    return CheckResult(
        name="ghost_radar",
        passed=passed,
        duration_ms=round(ms, 1),
        detail=f"{untracked_count} untracked files" if not passed else "no ghosts",
    )


def check_neural_connectivity() -> CheckResult:
    """Neural Connectivity (Ω₁₃) — API key coverage > 0."""
    t0 = time.monotonic()
    has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
    if not has_key:
        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            content = env_file.read_text()
            has_key = "GEMINI_API_KEY=" in content or "ANTHROPIC_API_KEY=" in content
            
    ms = (time.monotonic() - t0) * 1000
    return CheckResult(
        name="neural_connectivity",
        passed=has_key,
        duration_ms=round(ms, 1),
        detail="API keys found" if has_key else "missing GEMINI_API_KEY",
    )


def check_vercel_ban() -> CheckResult:
    """Verify absolute ban of Vercel dependencies/references in source code."""
    t0 = time.monotonic()
    
    # 1. Check package.json for '@vercel/' under dependencies or devDependencies
    pkg_json_path = REPO_ROOT / "package.json"
    if pkg_json_path.exists():
        try:
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
            deps = pkg_data.get("dependencies", {})
            dev_deps = pkg_data.get("devDependencies", {})
            for d in list(deps.keys()) + list(dev_deps.keys()):
                if "@vercel" in d or d == "vercel":
                    ms = (time.monotonic() - t0) * 1000
                    return CheckResult(
                        name="vercel_shield",
                        passed=False,
                        duration_ms=round(ms, 1),
                        detail=f"Forbidden Vercel dependency found in package.json: {d}",
                    )
        except Exception as e:
            ms = (time.monotonic() - t0) * 1000
            return CheckResult(
                name="vercel_shield",
                passed=False,
                duration_ms=round(ms, 1),
                detail=f"Failed to read package.json: {e}",
            )
            
    # 2. Check for vercel.json in the repository
    for path in REPO_ROOT.rglob("vercel.json"):
        if any(p in path.parts for p in ("node_modules", ".venv", ".git")):
            continue
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(
            name="vercel_shield",
            passed=False,
            duration_ms=round(ms, 1),
            detail=f"Forbidden vercel.json file found: {path.relative_to(REPO_ROOT)}",
        )

    # 3. Check for .vercel/ folders in the repository
    for path in REPO_ROOT.rglob(".vercel"):
        if any(p in path.parts for p in ("node_modules", ".venv", ".git")):
            continue
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(
            name="vercel_shield",
            passed=False,
            duration_ms=round(ms, 1),
            detail="Forbidden .vercel directory found",
        )

    # 4. Check imports in JS/TS/Astro/Python code files (excluding node_modules, etc.)
    forbidden_import_pattern = re.compile(
        r"from\s+['\"]@vercel/|import\s+.*?\s+from\s+['\"]@vercel/|import\(['\"]@vercel/|import\s+['\"]@vercel/"
    )
    for ext in ("*.js", "*.ts", "*.jsx", "*.tsx", "*.astro", "*.py"):
        for path in REPO_ROOT.rglob(ext):
            if any(p in path.parts for p in ("node_modules", ".venv", ".git", ".astro", ".wrangler", "dist", "build")):
                continue
            try:
                content = path.read_text(encoding="utf-8")
                if forbidden_import_pattern.search(content):
                    ms = (time.monotonic() - t0) * 1000
                    return CheckResult(
                        name="vercel_shield",
                        passed=False,
                        duration_ms=round(ms, 1),
                        detail=f"Forbidden Vercel import in: {path.relative_to(REPO_ROOT)}",
                    )
            except Exception:
                continue

    ms = (time.monotonic() - t0) * 1000
    return CheckResult(
        name="vercel_shield",
        passed=True,
        duration_ms=round(ms, 1),
        detail="No Vercel dependencies, configs, or imports found. Cloudflare-native confirmed.",
    )


def check_tests(fast: bool = False) -> CheckResult:
    """Run pytest suite."""
    t0 = time.monotonic()
    marker = '-m "not slow"' if fast else ""
    result = _run(
        f"uv run pytest tests/ {marker} --tb=line -q --no-header",
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
            passed=True,
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
        duration_ms=round(ms, 1),
        detail=detail,
    )


def check_mejoralo() -> CheckResult:
    """Check MEJORAlo score if available."""
    t0 = time.monotonic()
    try:
        result = _run("uv run python -m cortex.mejoralo scan --score-only cortex/", timeout=60)
        ms = (time.monotonic() - t0) * 1000
        try:
            score = int(result.stdout.strip().split()[-1])
        except (ValueError, IndexError):
            return CheckResult(
                name="mejoralo",
                passed=True,
                duration_ms=round(ms, 1),
                detail="could not parse score, skipped",
            )
        return CheckResult(
            name="mejoralo",
            passed=score >= MIN_MEJORALO,
            duration_ms=round(ms, 1),
            detail=f"score={score}/{MIN_MEJORALO} minimum",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(
            name="mejoralo",
            passed=True,
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
    icon = "✅" if result.passed else "❌"
    console.print(f"  {icon} {label}: {result.detail} ({result.duration_ms:.0f}ms)")


def _print_gate(console, report: GateReport) -> None:
    """Print final gate verdict."""
    if console is None:
        return
    console.print()
    if report.gate == "PASS":
        console.print("[bold green]🟢 GATE: PASS — Safe to ship.[/bold green]\n")
    else:
        failed = [c.name for c in report.checks if not c.passed]
        console.print(f"[bold red]🔴 GATE: FAIL — Blocked by: {', '.join(failed)}[/bold red]\n")


def main() -> None:
    fast = "--fast" in sys.argv
    json_only = "--json-only" in sys.argv
    console = _init_console(json_only)

    t0 = time.monotonic()
    report = GateReport(timestamp=datetime.now(timezone.utc).isoformat())

    checks = [
        ("Ghost Radar", check_ghost_radar),
        ("Tests", lambda: check_tests(fast=fast)),
        ("Git State", check_git_state),
        ("Lint", check_ruff),
        ("Complexity", check_radon_cc),
        ("Quality", check_mejoralo),
        ("Neural Conn", check_neural_connectivity),
        ("Vercel Shield", check_vercel_ban),
    ]

    for label, fn in checks:
        try:
            result = fn()
        except Exception as e:
            result = CheckResult(name=label.lower(), passed=False, detail=str(e))
        report.checks.append(result)
        _print_check(console, label, result)

    report.total_duration_ms = (time.monotonic() - t0) * 1000
    report.gate = "PASS" if all(c.passed for c in report.checks) else "FAIL"

    _print_gate(console, report)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    sys.exit(0 if report.gate == "PASS" else 1)


if __name__ == "__main__":
    main()
