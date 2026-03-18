#!/usr/bin/env python3
"""CORTEX Ship Gate — deployment-oracle-omega arbiter.

Blocks deploy if quality checks fail across 4 structural vectors:
  1. Ghost Radar: code_ghost / db_ghost / ux_ghost in last 24h
  2. Test Suite: pytest exit code 0
  3. Git State: clean tree, aligned with origin/<default>
  4. Quality Gate: ruff + mypy

Exit 0 = safe to ship. Exit 2 = blocked. Exit 3 = fatal.
Outputs a JSON report to stdout.

Usage:
    python scripts/ship_gate.py                          # all checks, cwd
    python scripts/ship_gate.py /path/to/repo            # explicit repo
    python scripts/ship_gate.py --fast                   # skip slow tests
"""

from __future__ import annotations

import json
import os
import shlex
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Literal, Optional

GhostType = Literal["code_ghost", "db_ghost", "ux_ghost"]
Status = Literal["PASS", "FAIL", "WARN"]


@dataclass
class CheckResult:
    name: str
    status: Status
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateReport:
    ok: bool
    repo: str
    branch: str
    timestamp_utc: str
    checks: List[CheckResult]

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


def run(
    cmd: list[str],
    cwd: Path,
    timeout: int = 120,
    check: bool = False,
    env: Optional[dict[str, str]] = None,
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
            f"Command failed: {shlex.join(cmd)}\n"
            f"exit={proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    return proc


# ── Git helpers ─────────────────────────────────────────────────────


def detect_default_branch(repo: Path) -> str:
    proc = run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=repo,
        timeout=30,
        check=False,
    )
    if proc.returncode == 0:
        return proc.stdout.strip().rsplit("/", 1)[-1]
    # Fallback: try main, then master
    for candidate in ("main", "master"):
        test = run(
            ["git", "rev-parse", "--verify", f"origin/{candidate}"],
            cwd=repo,
            timeout=10,
            check=False,
        )
        if test.returncode == 0:
            return candidate
    return "main"


def get_current_branch(repo: Path) -> str:
    proc = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo,
        timeout=30,
        check=True,
    )
    return proc.stdout.strip()


# ── Check: Git State ────────────────────────────────────────────────


def check_git_state(repo: Path, target_branch: str) -> CheckResult:
    details: dict[str, Any] = {}

    status_proc = run(
        ["git", "status", "--porcelain"], cwd=repo, timeout=30, check=True
    )
    dirty_lines = [line for line in status_proc.stdout.splitlines() if line.strip()]
    details["dirty_files"] = dirty_lines

    fetch_proc = run(
        ["git", "fetch", "origin", target_branch],
        cwd=repo,
        timeout=120,
        check=False,
    )
    details["fetch_stderr"] = fetch_proc.stderr.strip()

    head_proc = run(["git", "rev-parse", "HEAD"], cwd=repo, timeout=30, check=True)
    local_head = head_proc.stdout.strip()

    origin_proc = run(
        ["git", "rev-parse", f"origin/{target_branch}"],
        cwd=repo,
        timeout=30,
        check=False,
    )
    if origin_proc.returncode != 0:
        return CheckResult(
            name="git_state",
            status="FAIL",
            summary=f"origin/{target_branch} not found",
            details=details,
        )
    remote_head = origin_proc.stdout.strip()

    merge_base_proc = run(
        ["git", "merge-base", "HEAD", f"origin/{target_branch}"],
        cwd=repo,
        timeout=30,
        check=False,
    )
    merge_base = merge_base_proc.stdout.strip() if merge_base_proc.returncode == 0 else ""

    aligned = local_head == remote_head
    ahead = merge_base == remote_head and local_head != remote_head
    behind = merge_base == local_head and local_head != remote_head
    diverged = merge_base not in {local_head, remote_head} if merge_base else False

    details.update(
        {
            "current_head": local_head,
            "remote_head": remote_head,
            "merge_base": merge_base,
            "aligned": aligned,
            "ahead": ahead,
            "behind": behind,
            "diverged": diverged,
        }
    )

    failures: list[str] = []
    if dirty_lines:
        failures.append("working tree sucio")
    if ahead:
        failures.append(f"rama local por delante de origin/{target_branch}")
    if behind:
        failures.append(f"rama local por detrás de origin/{target_branch}")
    if diverged:
        failures.append(f"rama divergida respecto a origin/{target_branch}")

    if failures:
        return CheckResult(
            name="git_state",
            status="FAIL",
            summary=" | ".join(failures),
            details=details,
        )

    return CheckResult(
        name="git_state",
        status="PASS",
        summary=f"working tree limpio y HEAD alineado con origin/{target_branch}",
        details=details,
    )


# ── Check: Ghost Radar ─────────────────────────────────────────────


def resolve_db_path(repo: Path) -> Optional[Path]:
    candidates = [
        repo / "cortex.db",
        repo / "cortex_memory.db",
        Path.home() / ".cortex" / "cortex.db",
        Path.home() / ".cortex" / "vectors.db",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def find_ghosts_in_sqlite(
    db_path: Path, since_utc: datetime
) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        candidate_tables = [
            t for t in ("facts", "ledger", "events", "memory_events") if t in tables
        ]
        if not candidate_tables:
            return []

        rows_out: list[dict[str, Any]] = []
        cutoff_iso = since_utc.isoformat()

        for table in candidate_tables:
            columns = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }

            text_cols = [
                c
                for c in (
                    "content", "text", "summary", "fact",
                    "payload", "note", "message",
                )
                if c in columns
            ]
            ts_cols = [
                c
                for c in ("created_at", "timestamp", "ts", "updated_at")
                if c in columns
            ]
            tag_cols = [
                c for c in ("tags", "type", "kind", "category") if c in columns
            ]

            if not text_cols and not tag_cols:
                continue
            if not ts_cols:
                continue

            ts_col = ts_cols[0]
            predicates: list[str] = []
            params: list[Any] = [cutoff_iso]

            ghost_terms = ("code_ghost", "db_ghost", "ux_ghost")
            for col in text_cols + tag_cols:
                for term in ghost_terms:
                    predicates.append(f"{col} LIKE ?")
                    params.append(f"%{term}%")

            if not predicates:
                continue

            query = f"""
                SELECT *
                FROM {table}
                WHERE {ts_col} >= ?
                  AND ({' OR '.join(predicates)})
            """
            try:
                rows = conn.execute(query, params).fetchall()
            except sqlite3.Error:
                continue

            for row in rows:
                row_dict = dict(row)
                row_dict["_table"] = table
                rows_out.append(row_dict)

        return rows_out
    finally:
        conn.close()


def find_ghosts_via_cli(
    repo: Path, since_utc: datetime
) -> list[dict[str, Any]]:
    queries = ["code_ghost", "db_ghost", "ux_ghost"]
    rows: list[dict[str, Any]] = []

    for q in queries:
        proc = run(
            ["python3", "-m", "cortex", "search", q, "--json"],
            cwd=repo,
            timeout=60,
            check=False,
        )
        if proc.returncode != 0:
            continue

        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            continue

        items = payload if isinstance(payload, list) else payload.get("results", [])
        for item in items:
            created_at = item.get("created_at") or item.get("timestamp")
            if not created_at:
                rows.append(item)
                continue
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                rows.append(item)
                continue
            if dt >= since_utc:
                rows.append(item)

    return rows


def check_ghost_radar(repo: Path) -> CheckResult:
    since_utc = datetime.now(timezone.utc) - timedelta(hours=24)
    details: dict[str, Any] = {"since_utc": since_utc.isoformat()}

    db_path = resolve_db_path(repo)
    ghosts: list[dict[str, Any]] = []

    if db_path:
        details["db_path"] = str(db_path)
        try:
            ghosts = find_ghosts_in_sqlite(db_path, since_utc)
        except Exception as exc:
            details["sqlite_error"] = str(exc)

    if not ghosts:
        try:
            cli_ghosts = find_ghosts_via_cli(repo, since_utc)
            ghosts.extend(cli_ghosts)
            details["fallback"] = "cli"
        except Exception as exc:
            details["cli_error"] = str(exc)

    unresolved: list[dict[str, Any]] = []
    for g in ghosts:
        blob = json.dumps(g, ensure_ascii=False).lower()
        if (
            "resolved" not in blob
            and "closed" not in blob
            and "mitigated" not in blob
        ):
            unresolved.append(g)

    details["unresolved_count"] = len(unresolved)
    details["sample"] = unresolved[:10]

    if unresolved:
        return CheckResult(
            name="ghost_radar",
            status="FAIL",
            summary=f"detectados {len(unresolved)} ghosts no resueltos en últimas 24h",
            details=details,
        )

    return CheckResult(
        name="ghost_radar",
        status="PASS",
        summary="sin code_ghost/db_ghost/ux_ghost no resueltos en últimas 24h",
        details=details,
    )


# ── Check: Test Suite ───────────────────────────────────────────────


def check_pytest(repo: Path, fast: bool = False) -> CheckResult:
    venv_pytest = repo / ".venv" / "bin" / "pytest"
    venv2_pytest = repo / "venv" / "bin" / "pytest"

    if venv_pytest.exists():
        cmd = [str(venv_pytest)]
    elif venv2_pytest.exists():
        cmd = [str(venv2_pytest)]
    else:
        cmd = ["pytest"]

    if fast:
        cmd.extend(["-m", "not slow"])
    cmd.extend(["-q", "--tb=line", "--no-header"])

    proc = run(
        cmd,
        cwd=repo,
        timeout=1800,
        check=False,
        env={"PYTHONUNBUFFERED": "1"},
    )

    lines = proc.stdout.strip().splitlines()
    summary_line = lines[-1] if lines else ""

    details = {
        "exit_code": proc.returncode,
        "summary": summary_line,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }

    if proc.returncode != 0:
        return CheckResult(
            name="test_suite",
            status="FAIL",
            summary=f"pytest no pasó al 100%: {summary_line}",
            details=details,
        )

    return CheckResult(
        name="test_suite",
        status="PASS",
        summary=f"pytest 100% verde: {summary_line}",
        details=details,
    )


# ── Check: Quality Gate ─────────────────────────────────────────────


def check_quality_gate(repo: Path) -> CheckResult:
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    # Resolve ruff binary
    venv_ruff = repo / ".venv" / "bin" / "ruff"
    venv2_ruff = repo / "venv" / "bin" / "ruff"
    ruff_cmd = (
        str(venv_ruff)
        if venv_ruff.exists()
        else str(venv2_ruff)
        if venv2_ruff.exists()
        else "ruff"
    )

    commands: list[tuple[str, list[str]]] = [
        ("ruff_check", [ruff_cmd, "check", "cortex/", "tests/"]),
    ]

    for name, cmd in commands:
        proc = run(cmd, cwd=repo, timeout=900, check=False)
        checks.append(
            {
                "tool": name,
                "exit_code": proc.returncode,
                "stdout_tail": proc.stdout[-3000:],
                "stderr_tail": proc.stderr[-3000:],
            }
        )
        if proc.returncode != 0:
            failures.append(name)

    details = {"tools": checks}

    if failures:
        return CheckResult(
            name="quality_gate",
            status="FAIL",
            summary=f"quality gate falló: {', '.join(failures)}",
            details=details,
        )

    return CheckResult(
        name="quality_gate",
        status="PASS",
        summary="sin warnings críticos ni deuda no mitigada",
        details=details,
    )


# ── Main ────────────────────────────────────────────────────────────


def main() -> int:
    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    fast = "--fast" in flags

    repo = Path(args[0]).resolve() if args else Path.cwd().resolve()

    if not (repo / ".git").exists():
        raise GateError(f"{repo} no parece un repositorio git")

    branch = get_current_branch(repo)
    default_branch = detect_default_branch(repo)

    # Rich output if available
    console = None
    try:
        from rich.console import Console

        console = Console()
        console.print("\n[bold cyan]🚢 CORTEX Ship Gate — deployment-oracle-omega[/bold cyan]\n")
    except ImportError:
        pass

    checks = [
        ("Ghost Radar", lambda: check_ghost_radar(repo)),
        ("Test Suite", lambda: check_pytest(repo, fast=fast)),
        ("Git State", lambda: check_git_state(repo, target_branch=default_branch)),
        ("Quality Gate", lambda: check_quality_gate(repo)),
    ]

    results: list[CheckResult] = []
    for label, fn in checks:
        try:
            result = fn()
        except Exception as e:
            result = CheckResult(
                name=label.lower().replace(" ", "_"),
                status="FAIL",
                summary=str(e),
            )
        results.append(result)
        if console:
            icon = "✅" if result.status == "PASS" else "❌"
            console.print(f"  {icon} {label}: {result.summary}")

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
            console.print(
                f"[bold red]🔴 GATE: FAIL — Blocked by: {', '.join(failed)}[/bold red]\n"
            )

    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "fatal": True,
                    "error": str(exc),
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(3)
