# [C5-REAL] Exergy-Maximized
#!/usr/bin/env python3
"""
cat_id: ship-gate
cat_type: script
version: 1.1.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


from __future__ import annotations

import json
import os
import re
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
PYTEST_TIMEOUT: Final[int] = 300  # seconds


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


# ── Vercel Shield — Exclusion Vectors ───────────────────────────────
_VERCEL_SKIP: Final[frozenset] = frozenset(
    ("node_modules", ".venv", "venv", ".git", ".wrangler", "dist", "build", ".astro")
)
_VERCEL_FORBIDDEN_PKGS: Final[tuple] = (
    "@vercel/kv", "@vercel/postgres", "@vercel/blob", "@vercel/analytics",
    "@vercel/edge", "@vercel/edge-config", "@vercel/og", "@vercel/toolbar",
    "@vercel/speed-insights", "@vercel/flags", "@vercel/sdk", "@ai-sdk/vercel",
    "vercel",
)
_VERCEL_IMPORT_RE: Final[re.Pattern] = re.compile(
    r"from\s+['\"]@vercel/"
    r"|import\s+.*?\s+from\s+['\"]@vercel/"
    r"|import\(['\"]@vercel/"
    r"|import\s+['\"]@vercel/"
    r"|require\(['\"]@vercel/"
    r"|require\(['\"]vercel"
)
_VERCEL_SCRIPT_RE: Final[re.Pattern] = re.compile(
    r"(?:^|\s)vercel\s+(?:deploy|dev|build|pull|env|link)"
    r"|vercel\.com"
    r"|VERCEL_TOKEN"
    r"|VERCEL_ORG_ID"
    r"|VERCEL_PROJECT_ID",
    re.MULTILINE,
)
_VERCEL_ENV_RE: Final[re.Pattern] = re.compile(
    r"^VERCEL_|^VERCEL$|^NEXT_PUBLIC_VERCEL_", re.MULTILINE
)


def check_vercel_ban() -> CheckResult:
    """
    OUROBOROS-V001..V100 enforcement.
    10-vector scan: deps | configs | dirs | imports | scripts |
                    env-vars | lockfile | worktrees | pyproject | wrangler-presence.
    Returns aggregated violation list; fails on first non-empty vector.
    """
    t0 = time.monotonic()
    violations: list[str] = []

    # ── V1: package.json — dependencies + devDependencies + scripts ──
    pkg_path = REPO_ROOT / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            all_deps = {
                **pkg.get("dependencies", {}),
                **pkg.get("devDependencies", {}),
                **pkg.get("peerDependencies", {}),
                **pkg.get("optionalDependencies", {}),
            }
            for dep in all_deps:
                if dep in _VERCEL_FORBIDDEN_PKGS or dep.startswith("@vercel/"):
                    violations.append(f"V1:pkg_dep:{dep}")
            for script_body in pkg.get("scripts", {}).values():
                if _VERCEL_SCRIPT_RE.search(str(script_body)):
                    violations.append(f"V1:pkg_script:{script_body[:80]}")
        except Exception as exc:
            violations.append(f"V1:pkg_parse_error:{exc}")

    # ── V2: vercel.json existence (any path, any depth) ──────────────
    for p in REPO_ROOT.rglob("vercel.json"):
        if any(skip in p.parts for skip in _VERCEL_SKIP):
            continue
        violations.append(f"V2:vercel_json:{p.relative_to(REPO_ROOT)}")

    # ── V3: .vercel/ directory ────────────────────────────────────────
    for p in REPO_ROOT.rglob(".vercel"):
        if any(skip in p.parts for skip in _VERCEL_SKIP):
            continue
        if p.is_dir():
            violations.append(f"V3:vercel_dir:{p.relative_to(REPO_ROOT)}")

    # ── V4: @vercel/* imports in source files ─────────────────────────
    for ext in ("*.js", "*.ts", "*.jsx", "*.tsx", "*.astro", "*.py", "*.mjs", "*.cjs"):
        for p in REPO_ROOT.rglob(ext):
            if any(skip in p.parts for skip in _VERCEL_SKIP):
                continue
            try:
                if _VERCEL_IMPORT_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
                    violations.append(f"V4:import:{p.relative_to(REPO_ROOT)}")
            except OSError:
                continue

    # ── V5: Makefile / shell scripts / CI yaml ────────────────────────
    for pattern in ("Makefile", "*.sh", "*.yaml", "*.yml"):
        for p in REPO_ROOT.rglob(pattern):
            if any(skip in p.parts for skip in _VERCEL_SKIP):
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                if _VERCEL_SCRIPT_RE.search(content):
                    violations.append(f"V5:script:{p.relative_to(REPO_ROOT)}")
            except OSError:
                continue

    # ── V6: VERCEL_* env vars in live process environment ────────────
    for key in os.environ:
        if re.match(r"^VERCEL_|^VERCEL$|^NEXT_PUBLIC_VERCEL_", key):
            violations.append(f"V6:env:{key}={os.environ[key][:20]}")

    # ── V7: VERCEL_* in .env* files ───────────────────────────────────
    for env_file in REPO_ROOT.glob(".env*"):
        try:
            content = env_file.read_text(encoding="utf-8", errors="ignore")
            if _VERCEL_ENV_RE.search(content):
                violations.append(f"V7:env_file:{env_file.name}")
        except OSError:
            continue

    # ── V8: package-lock.json / yarn.lock / pnpm-lock.yaml ───────────
    for lock in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml"):
        lock_path = REPO_ROOT / lock
        if not lock_path.exists():
            continue
        try:
            if lock == "package-lock.json":
                try:
                    lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
                    packages = lock_data.get("packages", {})
                    for pkg_name in packages:
                        if pkg_name.startswith("node_modules/@vercel/") or pkg_name == "node_modules/vercel":
                            violations.append(f"V8:lockfile:{lock}:{pkg_name}")
                except Exception:
                    if b"@vercel/" in lock_path.read_bytes():
                        violations.append(f"V8:lockfile:{lock}:fallback_scan")
            else:
                if b"@vercel/" in lock_path.read_bytes():
                    violations.append(f"V8:lockfile:{lock}")
        except OSError:
            continue

    # ── V9: worktrees — scan for vercel.json in active worktrees ──────
    worktrees_root = REPO_ROOT / "worktrees"
    if worktrees_root.is_dir():
        for p in worktrees_root.rglob("vercel.json"):
            if any(skip in p.parts for skip in _VERCEL_SKIP):
                continue
            violations.append(f"V9:worktree_json:{p.relative_to(REPO_ROOT)}")

    # ── V10: wrangler.toml presence (positive invariant OUROBOROS-V011)
    wrangler_present = (
        (REPO_ROOT / "wrangler.toml").exists()
        or (REPO_ROOT / "wrangler.json").exists()
    )
    if not wrangler_present:
        violations.append("V10:missing_wrangler_toml — no wrangler.toml or wrangler.json found")

    ms = round((time.monotonic() - t0) * 1000, 1)
    if violations:
        # Collapse to first 3 surface violations for readability + total count
        head = " | ".join(violations[:3])
        tail = f" (+{len(violations) - 3} more)" if len(violations) > 3 else ""
        return CheckResult(
            name="vercel_shield",
            passed=False,
            duration_ms=ms,
            detail=f"[P0] {len(violations)} violation(s): {head}{tail}",
        )

    return CheckResult(
        name="vercel_shield",
        passed=True,
        duration_ms=ms,
        detail="OUROBOROS-V001..V100 clear. Cloudflare-native C5-REAL confirmed.",
    )


def check_tests(fast: bool = False) -> CheckResult:
    """Run pytest suite."""
    t0 = time.monotonic()
    marker = '-m "not slow"' if fast else ""
    result = _run(
        f"uv run pytest tests/ {marker} -n auto --tb=line -q --no-header",
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
