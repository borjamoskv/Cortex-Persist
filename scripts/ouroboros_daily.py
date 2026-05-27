#!/usr/bin/env python3
"""
OUROBOROS-∞ Daily Metabolism — Autonomous Self-Improvement Cron
==============================================================

Runs daily via launchd. Scans the cortex-persist codebase, diagnoses entropy,
triages the worst offenders, and (optionally) metabolizes them.

Usage:
    python3 ouroboros_daily.py              # Diagnose + report (safe, no mutations)
    python3 ouroboros_daily.py --commit     # Diagnose + metabolize top-5 (ACID rollback)
    python3 ouroboros_daily.py --top 10     # Override number of files to metabolize
    python3 ouroboros_daily.py --verbose    # Full logging

Reality Level: C5-REAL (operates on actual source files)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORTEX_CORE = PROJECT_ROOT / "cortex-core"
CORTEX_EXT = PROJECT_ROOT / "cortex" / "extensions"
REPORTS_DIR = PROJECT_ROOT / ".scratch" / "ouroboros" / "daily_reports"

# Add project root to path for imports
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("ouroboros.daily")


# ── Exclusion patterns ─────────────────────────────────────────────
EXCLUDE_DIRS = {
    "__pycache__",
    ".scratch",
    ".git",
    ".venv",
    "node_modules",
    ".agent",
    "compiled_skills",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
}

EXCLUDE_FILES = {
    "__init__.py",
    "conftest.py",
    "setup.py",
}


def discover_python_files() -> list[Path]:
    """Find all Python files in cortex-persist, excluding noise."""
    targets: list[Path] = []

    scan_dirs = [
        CORTEX_CORE,
        CORTEX_EXT,
        PROJECT_ROOT / "cortex" / "routes",
        PROJECT_ROOT / "cortex" / "core",
    ]

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            # Skip excluded directories
            if any(part in EXCLUDE_DIRS for part in py_file.parts):
                continue
            # Skip excluded files
            if py_file.name in EXCLUDE_FILES:
                continue
            # Skip test files (separate concern)
            if py_file.name.startswith("test_"):
                continue
            # Skip empty files
            if py_file.stat().st_size < 50:
                continue
            targets.append(py_file)

    return sorted(targets)


async def diagnose_file(file_path: Path) -> dict:
    """Run OuroborosOmega diagnosis on a single file."""
    try:
        from cortex.extensions.evolution.ouroboros_omega import OuroborosOmega

        engine = OuroborosOmega(
            str(file_path),
            project_root=str(PROJECT_ROOT),
            dry_run=True,
        )
        diagnosis = await engine.diagnose()

        return {
            "file": str(file_path.relative_to(PROJECT_ROOT)),
            "entropy": round(diagnosis.entropy_score, 2),
            "loc": diagnosis.loc,
            "complexity_hotspots": {
                k: v
                for k, v in sorted(
                    diagnosis.mccabe_complexity.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
            },
            "dead_interfaces": list(diagnosis.dead_interfaces)[:5],
            "unused_imports": list(diagnosis.imports - diagnosis.used_imports)[:5],
            "blocking_calls": diagnosis.blocking_calls,
            "nesting_max": max(diagnosis.nesting_depths.values())
            if diagnosis.nesting_depths
            else 0,
            "status": "OK",
        }
    except Exception as e:
        return {
            "file": str(file_path.relative_to(PROJECT_ROOT)),
            "entropy": -1,
            "error": str(e),
            "status": "ERROR",
        }


async def metabolize_file(file_path: Path, dry_run: bool = True) -> dict:
    """Run full OuroborosOmega ACID cycle on a file."""
    try:
        from cortex.extensions.evolution.ouroboros_omega import OuroborosOmega

        engine = OuroborosOmega(
            str(file_path),
            project_root=str(PROJECT_ROOT),
            dry_run=dry_run,
        )
        result = await engine.execute_atomic_cycle()
        return {
            "file": str(file_path.relative_to(PROJECT_ROOT)),
            **result,
        }
    except Exception as e:
        return {
            "file": str(file_path.relative_to(PROJECT_ROOT)),
            "status": "ERROR",
            "reason": str(e),
        }


def run_gate_check() -> dict:
    """Run OuroborosGate entropy measurement on CORTEX DB."""
    try:
        import sqlite3
        from cortex.config import DB_PATH

        if not Path(DB_PATH).exists():
            return {"status": "SKIP", "reason": "DB not found"}

        conn = sqlite3.connect(DB_PATH)
        from cortex.extensions.gate.ouroboros import OuroborosGate

        gate = OuroborosGate(conn)
        entropy = gate.measure_entropy()
        dead_weight = gate.identify_dead_weight()
        conn.close()

        return {
            "status": "OK",
            "entropy_metrics": entropy,
            "dead_weight_candidate": dead_weight,
        }
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}


def generate_report(
    diagnoses: list[dict],
    metabolisms: list[dict],
    gate_result: dict,
    elapsed: float,
) -> dict:
    """Generate the daily metabolism report."""
    ok_diagnoses = [d for d in diagnoses if d["status"] == "OK"]
    error_diagnoses = [d for d in diagnoses if d["status"] == "ERROR"]

    # Sort by entropy descending
    ok_diagnoses.sort(key=lambda d: d["entropy"], reverse=True)

    avg_entropy = sum(d["entropy"] for d in ok_diagnoses) / len(ok_diagnoses) if ok_diagnoses else 0

    total_blocking = sum(len(d.get("blocking_calls", [])) for d in ok_diagnoses)
    total_dead = sum(len(d.get("dead_interfaces", [])) for d in ok_diagnoses)
    total_unused = sum(len(d.get("unused_imports", [])) for d in ok_diagnoses)

    report = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "summary": {
            "files_scanned": len(diagnoses),
            "files_ok": len(ok_diagnoses),
            "files_error": len(error_diagnoses),
            "avg_entropy": round(avg_entropy, 2),
            "total_blocking_calls": total_blocking,
            "total_dead_interfaces": total_dead,
            "total_unused_imports": total_unused,
        },
        "top_entropy": ok_diagnoses[:10],
        "errors": error_diagnoses[:5],
        "metabolisms": metabolisms,
        "gate": gate_result,
    }

    return report


def save_report(report: dict) -> Path:
    """Save daily report to disk."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"ouroboros_{date_str}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    return report_path


def print_summary(report: dict):
    """Print human-readable summary to stdout."""
    s = report["summary"]
    print("\n" + "=" * 60)
    print("  OUROBOROS-∞ DAILY METABOLISM REPORT")
    print("=" * 60)
    print(f"  Timestamp:          {report['timestamp']}")
    print(f"  Elapsed:            {report['elapsed_seconds']}s")
    print(f"  Files scanned:      {s['files_scanned']}")
    print(f"  Files OK:           {s['files_ok']}")
    print(f"  Files ERROR:        {s['files_error']}")
    print(f"  Avg entropy:        {s['avg_entropy']:.2f}")
    print(f"  Blocking calls:     {s['total_blocking_calls']}")
    print(f"  Dead interfaces:    {s['total_dead_interfaces']}")
    print(f"  Unused imports:     {s['total_unused_imports']}")
    print("-" * 60)

    print("\n  TOP ENTROPY FILES:")
    for i, d in enumerate(report["top_entropy"][:5], 1):
        print(f"  {i}. [{d['entropy']:.1f}] {d['file']} ({d['loc']} LOC)")
        if d.get("complexity_hotspots"):
            hotspot = max(d["complexity_hotspots"].items(), key=lambda x: x[1])
            print(f"     └─ Hotspot: {hotspot[0]} (McCabe={hotspot[1]})")

    if report["metabolisms"]:
        print("\n  METABOLISMS:")
        for m in report["metabolisms"]:
            status = m.get("status", "UNKNOWN")
            delta = m.get("delta", "N/A")
            print(f"  → {m['file']}: {status} (Δ={delta})")

    gate = report["gate"]
    if gate["status"] == "OK":
        metrics = gate["entropy_metrics"]
        print("\n  GATE STATUS:")
        print(f"  SNR:            {metrics['signal_to_noise']}")
        print(f"  Entropy Index:  {metrics['entropy_index']}")
        print(f"  Total Facts:    {metrics['total_facts']}")
        if gate.get("dead_weight_candidate"):
            print(f"  ⚠ Dead Weight:  {gate['dead_weight_candidate']}")

    print("=" * 60)
    print()


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="OUROBOROS-∞ Daily Metabolism")
    parser.add_argument(
        "--commit", action="store_true", help="Actually mutate files (default: dry-run)"
    )
    parser.add_argument(
        "--top", type=int, default=5, help="Number of files to metabolize (default: 5)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    start = time.monotonic()

    # 1. SCAN
    logger.info("Phase 1: SCAN")
    files = discover_python_files()
    logger.info("Found %d Python files", len(files))

    if not files:
        print("No Python files found. Exiting.")
        return

    # 2. DIAGNOSE
    logger.info("Phase 2: DIAGNOSE")
    diagnoses = await asyncio.gather(*[diagnose_file(f) for f in files])
    diagnoses = list(diagnoses)

    # 3. TRIAGE
    logger.info("Phase 3: TRIAGE")
    ok_diagnoses = [d for d in diagnoses if d["status"] == "OK"]
    ok_diagnoses.sort(key=lambda d: d["entropy"], reverse=True)

    # 4. METABOLIZE (top N by entropy)
    metabolisms = []
    if ok_diagnoses:
        top_files = ok_diagnoses[: args.top]
        logger.info("Phase 4: METABOLIZE (top %d)", len(top_files))

        for diag in top_files:
            file_path = PROJECT_ROOT / diag["file"]
            dry_run = not args.commit
            result = await metabolize_file(file_path, dry_run=dry_run)
            metabolisms.append(result)

    # 5. GATE CHECK
    logger.info("Phase 5: GATE")
    gate_result = run_gate_check()

    elapsed = time.monotonic() - start

    # 6. REPORT
    report = generate_report(diagnoses, metabolisms, gate_result, elapsed)
    report_path = save_report(report)

    print_summary(report)
    print(f"  Report saved: {report_path}")

    # 7. PERSIST (best-effort)
    try:
        import subprocess

        cortex_cli = PROJECT_ROOT / ".venv" / "bin" / "python"
        if cortex_cli.exists():
            avg_e = report["summary"]["avg_entropy"]
            n = report["summary"]["files_scanned"]
            subprocess.run(
                [
                    str(cortex_cli),
                    "-m",
                    "cortex.cli",
                    "store",
                    "--type",
                    "decision",
                    "--source",
                    "ag:ouroboros-daily",
                    "cortex",
                    f"OUROBOROS-DAILY: {n} files scanned, avg_entropy={avg_e:.2f}, "
                    f"top_entropy={ok_diagnoses[0]['entropy']:.2f} ({ok_diagnoses[0]['file']})"
                    if ok_diagnoses
                    else "no files",
                ],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                timeout=10,
            )
    except Exception:
        pass  # Best-effort persistence


if __name__ == "__main__":
    asyncio.run(main())
