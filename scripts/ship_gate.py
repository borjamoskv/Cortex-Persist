#!/usr/bin/env python3
"""CORTEX Ship Gate — deployment-oracle-omega arbiter.

4-vector structural gate:
  1. Ghost Radar   2. Test Suite   3. Git State   4. Quality Gate

Exit 0 = PASS. Exit 2 = FAIL. Exit 3 = fatal error.
"""

from __future__ import annotations

import json
import os
import shlex
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

Status = Literal["PASS", "FAIL", "WARN"]

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


@dataclass
class CheckResult:
    name: str
    status: Status
    summary: str
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateReport:
    ok: bool
    repo: str
    branch: str
    timestamp_utc: str
    checks: list[CheckResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "repo": self.repo,
            "branch": self.branch,
            "timestamp_utc": self.timestamp_utc,
            "checks": [asdict(c) for c in self.checks],
        }


class GateError(RuntimeError):
    pass


def _run(
    cmd: list[str],
    cwd: Path,
    timeout: int = 120,
    check: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=merged_env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise GateError(
            f"Command failed: {shlex.join(cmd)}\nexit={proc.returncode}\nstderr:\n{proc.stderr}"
        )
    return proc


# ── Git ─────────────────────────────────────────────────────────────


def _default_branch(repo: Path) -> str:
    proc = _run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo, check=False)
    if proc.returncode == 0:
        return proc.stdout.strip().rsplit("/", 1)[-1]
    for c in ("main", "master"):
        t = _run(["git", "rev-parse", "--verify", f"origin/{c}"], cwd=repo, check=False)
        if t.returncode == 0:
            return c
    return "main"


def _current_branch(repo: Path) -> str:
    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo, check=True).stdout.strip()


def check_git_state(repo: Path, target: str) -> CheckResult:
    t0 = time.monotonic()
    d: dict[str, Any] = {}

    status_out = _run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
    ).stdout.splitlines()
    dirty = [ln for ln in status_out if ln.strip()]
    d["dirty_files"] = dirty[:20]

    _run(["git", "fetch", "origin", target], cwd=repo, timeout=120, check=False)

    local = _run(["git", "rev-parse", "HEAD"], cwd=repo, check=True).stdout.strip()
    rp = _run(["git", "rev-parse", f"origin/{target}"], cwd=repo, check=False)
    remote = rp.stdout.strip() if rp.returncode == 0 else ""

    mb_proc = _run(["git", "merge-base", "HEAD", f"origin/{target}"], cwd=repo, check=False)
    mb = mb_proc.stdout.strip() if mb_proc.returncode == 0 else ""

    ahead = mb == remote and local != remote
    behind = mb == local and local != remote
    diverged = mb not in {local, remote} if mb else False
    d.update(
        {
            "local": local[:12],
            "remote": remote[:12],
            "ahead": ahead,
            "behind": behind,
            "diverged": diverged,
        }
    )

    fails = []
    if dirty:
        fails.append(f"working tree sucio ({len(dirty)} files)")
    if ahead:
        fails.append(f"ahead of origin/{target}")
    if behind:
        fails.append(f"behind origin/{target}")
    if diverged:
        fails.append(f"diverged from origin/{target}")

    ms = (time.monotonic() - t0) * 1000
    if fails:
        return CheckResult("git_state", "FAIL", " | ".join(fails), ms, d)
    return CheckResult("git_state", "PASS", f"clean & aligned with origin/{target}", ms, d)


# ── Ghost Radar ─────────────────────────────────────────────────────


def check_ghost_radar(repo: Path) -> CheckResult:
    t0 = time.monotonic()
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    d: dict[str, Any] = {"since_utc": since.isoformat()}

    # Try SQLite
    db_candidates = [
        repo / "cortex.db",
        repo / "cortex_memory.db",
        Path.home() / ".cortex" / "cortex.db",
    ]
    ghosts: list[dict[str, Any]] = []
    for db_path in db_candidates:
        if not db_path.exists():
            continue
        d["db_path"] = str(db_path)
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            tables = {
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            for tbl in [t for t in ("facts", "ledger", "events") if t in tables]:
                cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
                ts_col = next((c for c in ("created_at", "timestamp", "ts") if c in cols), None)
                text_cols = [
                    c for c in ("content", "summary", "fact", "type", "tags", "kind") if c in cols
                ]
                if not ts_col or not text_cols:
                    continue
                preds = []
                params: list[Any] = [since.isoformat()]
                for col in text_cols:
                    for term in ("code_ghost", "db_ghost", "ux_ghost"):
                        preds.append(f"{col} LIKE ?")
                        params.append(f"%{term}%")
                if preds:
                    try:
                        rows = conn.execute(
                            f"SELECT * FROM {tbl} WHERE {ts_col} >= ? AND ({' OR '.join(preds)})",
                            params,
                        ).fetchall()
                        ghosts.extend(dict(r) for r in rows)
                    except sqlite3.Error:
                        pass
            conn.close()
        except Exception as e:
            d["sqlite_error"] = str(e)
        if ghosts:
            break

    # Filter unresolved
    unresolved = [
        g
        for g in ghosts
        if not any(
            k in json.dumps(g, ensure_ascii=False).lower()
            for k in ("resolved", "closed", "mitigated")
        )
    ]
    d["unresolved_count"] = len(unresolved)
    ms = (time.monotonic() - t0) * 1000

    if unresolved:
        return CheckResult(
            "ghost_radar", "FAIL", f"{len(unresolved)} unresolved ghosts in 24h", ms, d
        )
    return CheckResult("ghost_radar", "PASS", "no unresolved ghosts in 24h", ms, d)


# ── Test Suite ──────────────────────────────────────────────────────


def check_pytest(repo: Path, fast: bool = False) -> CheckResult:
    t0 = time.monotonic()
    for venv in (repo / ".venv" / "bin" / "pytest", repo / "venv" / "bin" / "pytest"):
        if venv.exists():
            cmd = [str(venv)]
            break
    else:
        cmd = ["pytest"]

    cmd.extend(["tests/", "-q", "--tb=line", "--no-header"])
    if fast:
        cmd.extend(["-m", "not slow"])

    proc = _run(cmd, cwd=repo, timeout=600, check=False, env={"PYTHONUNBUFFERED": "1"})
    lines = proc.stdout.strip().splitlines()
    summary = lines[-1] if lines else proc.stderr.strip()[:200]
    ms = (time.monotonic() - t0) * 1000

    d = {"exit_code": proc.returncode, "summary": summary}
    if proc.returncode != 0:
        return CheckResult("test_suite", "FAIL", f"pytest failed: {summary}", ms, d)
    return CheckResult("test_suite", "PASS", f"pytest green: {summary}", ms, d)


# ── Quality Gate ────────────────────────────────────────────────────


def check_quality(repo: Path) -> CheckResult:
    t0 = time.monotonic()
    for venv in (repo / ".venv" / "bin" / "ruff", repo / "venv" / "bin" / "ruff"):
        if venv.exists():
            ruff = str(venv)
            break
    else:
        ruff = "ruff"

    proc = _run([ruff, "check", "cortex/", "tests/"], cwd=repo, timeout=120, check=False)
    ms = (time.monotonic() - t0) * 1000
    violations = len(proc.stdout.strip().splitlines()) if proc.returncode != 0 else 0

    d = {"exit_code": proc.returncode, "violations": violations}
    if proc.returncode != 0:
        return CheckResult("quality_gate", "FAIL", f"ruff: {violations} violations", ms, d)
    return CheckResult("quality_gate", "PASS", "ruff clean", ms, d)


# ── Neural Connectivity (Ω₁₃) ──────────────────────────────────────


def check_connectivity(repo: Path) -> CheckResult:
    """Check API key coverage — thermodynamic exergy gate."""
    t0 = time.monotonic()
    d: dict[str, Any] = {}
    presets_path = repo / "config" / "llm_presets.json"

    if not presets_path.exists():
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(
            "neural_connectivity",
            "WARN",
            "llm_presets.json not found",
            ms,
            d,
        )

    try:
        with open(presets_path, encoding="utf-8") as f:
            presets = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(
            "neural_connectivity",
            "FAIL",
            f"presets parse error: {e}",
            ms,
            d,
        )

    frontier_keys = []
    configured = []
    total = 0

    for provider, cfg in presets.items():
        tier = cfg.get("tier", "unknown")
        if tier == "local":
            continue
        env_key = cfg.get("env_key")
        if not env_key:
            continue
        total += 1
        if os.getenv(env_key):
            configured.append(provider)
        if tier == "frontier" and os.getenv(env_key):
            frontier_keys.append(provider)

    coverage = (len(configured) / total * 100) if total > 0 else 0
    d.update(
        {
            "total": total,
            "configured": len(configured),
            "coverage_pct": round(coverage, 1),
            "frontier_active": frontier_keys,
        }
    )
    ms = (time.monotonic() - t0) * 1000

    if not configured:
        return CheckResult(
            "neural_connectivity",
            "FAIL",
            "zero API keys configured — dead system",
            ms,
            d,
        )
    if not frontier_keys:
        return CheckResult(
            "neural_connectivity",
            "WARN",
            f"{len(configured)}/{total} keys but no frontier",
            ms,
            d,
        )
    return CheckResult(
        "neural_connectivity",
        "PASS",
        f"{coverage:.0f}% coverage ({len(configured)}/{total})",
        ms,
        d,
    )


# ── Main ────────────────────────────────────────────────────────────


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    fast = "--fast" in flags

    repo = Path(args[0]).resolve() if args else REPO_ROOT
    if not (repo / ".git").exists():
        raise GateError(f"{repo} is not a git repository")

    branch = _current_branch(repo)
    default = _default_branch(repo)

    # Rich output
    console = None
    try:
        from rich.console import Console

        console = Console()
        console.print("\n[bold cyan]🚢 CORTEX Ship Gate — deployment-oracle-omega[/bold cyan]\n")
    except ImportError:
        pass

    gate_checks = [
        ("Ghost Radar", lambda: check_ghost_radar(repo)),
        ("Test Suite", lambda: check_pytest(repo, fast=fast)),
        ("Git State", lambda: check_git_state(repo, target=default)),
        ("Quality Gate", lambda: check_quality(repo)),
        ("Neural Connectivity", lambda: check_connectivity(repo)),
    ]

    results: list[CheckResult] = []
    for label, fn in gate_checks:
        try:
            r = fn()
        except Exception as e:
            r = CheckResult(label.lower().replace(" ", "_"), "FAIL", str(e))
        results.append(r)
        if console:
            icon = "✅" if r.status == "PASS" else "❌"
            console.print(f"  {icon} {label}: {r.summary} ({r.duration_ms:.0f}ms)")

    ok = all(c.status == "PASS" for c in results)
    report = GateReport(
        ok=ok,
        repo=str(repo),
        branch=branch,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        checks=results,
    )

    if console:
        console.print()
        if ok:
            console.print("[bold green]🟢 GATE: PASS — Safe to deploy.[/bold green]\n")
        else:
            failed = [c.name for c in results if c.status != "PASS"]
            console.print(f"[bold red]🔴 GATE: FAIL — Blocked by: {', '.join(failed)}[/bold red]\n")

    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(
            json.dumps({"ok": False, "fatal": True, "error": str(exc)}, indent=2), file=sys.stderr
        )
        raise SystemExit(3) from exc
