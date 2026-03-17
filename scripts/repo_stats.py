#!/usr/bin/env python3
"""
scripts/repo_stats.py
Generates a machine-readable artifact with verifiable repository metrics.
Output: artifacts/stats.json

Usage:
    python scripts/repo_stats.py
    python scripts/repo_stats.py --out artifacts/stats.json
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent

CORE_PATHS = [
    ROOT / "cortex",
    ROOT / "tests",
]


def count_python_files(paths: list[Path]) -> tuple[int, int]:
    """Count .py files and total LOC across the given paths."""
    total_files = 0
    total_loc = 0
    for base in paths:
        for f in base.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            total_files += 1
            try:
                total_loc += len(f.read_text(encoding="utf-8", errors="ignore").splitlines())
            except OSError:
                pass
    return total_files, total_loc


def count_python_modules(paths: list[Path]) -> int:
    """Count importable modules (files with at least one class or function)."""
    count = 0
    for base in paths:
        for f in base.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
                if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for n in ast.walk(tree)):
                    count += 1
            except SyntaxError:
                pass
    return count


def count_tests() -> dict[str, int]:
    """Count test functions using pytest's collect-only."""
    tests_path = ROOT / "tests"
    if not tests_path.exists():
        return {"collected": 0}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(tests_path), "--collect-only", "-q", "--no-header"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=120,
        )
        lines = result.stdout.strip().splitlines()
        # Last line: "N tests collected in X.Xs"
        for line in reversed(lines):
            if "selected" in line or "collected" in line:
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        return {"collected": int(part)}
    except Exception:
        pass
    return {"collected": -1}  # -1 signals measurement failure


def run_benchmark_sample() -> dict[str, float]:
    """Run a minimal in-process SQLite insert+read timing sample."""
    import sqlite3
    import statistics
    import tempfile

    samples = 30
    latencies: list[float] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "bench.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE bench (id INTEGER PRIMARY KEY AUTOINCREMENT, val TEXT)")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.commit()

        for i in range(samples):
            t0 = time.perf_counter()
            conn.execute("INSERT INTO bench (val) VALUES (?)", (f"item-{i}",))
            conn.execute("SELECT val FROM bench WHERE id = last_insert_rowid()")
            conn.commit()
            latencies.append((time.perf_counter() - t0) * 1000)

        conn.close()

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    return {"benchmark_sqlite_rw_p50_ms": round(p50, 2), "benchmark_sqlite_rw_p95_ms": round(p95, 2)}


def main(out_path: Path | None = None) -> None:
    out_path = out_path or ROOT / "artifacts" / "stats.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("→ Counting Python files and LOC...")
    files, loc = count_python_files(CORE_PATHS)

    print("→ Counting modules...")
    modules = count_python_modules(CORE_PATHS)

    print("→ Counting tests (pytest collect)...")
    test_info = count_tests()

    print("→ Running SQLite RW benchmark...")
    bench = run_benchmark_sample()

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python_files_core": files,
        "python_modules_core": modules,
        "loc_python_core": loc,
        "tests_collected": test_info["collected"],
        **bench,
    }

    out_path.write_text(json.dumps(stats, indent=2))
    print(f"\n✓ Stats written to: {out_path}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate verifiable repo metrics.")
    parser.add_argument("--out", type=Path, default=None, help="Output JSON path")
    args = parser.parse_args()
    main(args.out)
