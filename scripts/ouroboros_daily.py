#!/usr/bin/env python3
"""
Ouroboros-Infinity: Daily Autopoietic Metabolism Loop.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
import time
from pathlib import Path
import sys
import os

# Ensure the root of cortex-persist is in PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cortex.ouroboros.daily")

from cortex.cli.common import get_engine
from cortex.extensions.evolution.ouroboros_omega import OuroborosOmega
from cortex.extensions.gate.ouroboros import OuroborosGate

async def main():
    parser = argparse.ArgumentParser(description="Ouroboros-Infinity Daily Metabolism")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--apply", action="store_true", help="Actually execute mutation (dry_run=False)")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    start_time = time.perf_counter()
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. SCAN — Find all Python files in cortex-persist (exclude tests, __pycache__, .scratch, .venv, node_modules)
    python_files = []
    exclude_dirs = {
        "tests", "__pycache__", ".scratch", ".venv", ".git", "node_modules", "build", "dist"
    }
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Exclude directories in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
        for file in files:
            if file.endswith(".py"):
                full_path = Path(root) / file
                # Exclude tests just in case
                if "tests/" not in str(full_path) and "test_" not in file:
                    python_files.append(full_path)
                    
    logger.info("Found %d Python files to scan.", len(python_files))
    
    # 2. DIAGNOSE & TRIAGE
    diagnoses = []
    errors = []
    
    for file_path in python_files:
        rel_path = file_path.relative_to(PROJECT_ROOT)
        try:
            # We use OuroborosOmega to diagnose
            omega = OuroborosOmega(
                target_path=str(file_path),
                project_root=str(PROJECT_ROOT),
                dry_run=True
            )
            diag = await omega.diagnose()
            
            # Group complexity hotspots
            complexity_hotspots = diag.mccabe_complexity
            nesting_max = max(diag.nesting_depths.values()) if diag.nesting_depths else 0
            
            diagnoses.append({
                "file": str(rel_path),
                "entropy": diag.entropy_score,
                "loc": diag.loc,
                "complexity_hotspots": complexity_hotspots,
                "dead_interfaces": list(diag.dead_interfaces),
                "unused_imports": list(diag.imports - diag.used_imports),
                "blocking_calls": diag.blocking_calls,
                "nesting_max": nesting_max,
                "status": "OK"
            })
        except Exception as e:
            logger.error("Error diagnosing %s: %s", rel_path, e)
            errors.append({
                "file": str(rel_path),
                "error": f"{type(e).__name__}: {str(e)}"
            })
            diagnoses.append({
                "file": str(rel_path),
                "entropy": 0.0,
                "loc": 0,
                "complexity_hotspots": {},
                "dead_interfaces": [],
                "unused_imports": [],
                "blocking_calls": [],
                "nesting_max": 0,
                "status": f"ERROR: {type(e).__name__}"
            })

    # Sort by entropy descending
    diagnoses.sort(key=lambda x: x["entropy"], reverse=True)
    
    # 3. METABOLIZE — Run OuroborosOmega on top-5 highest entropy files
    top_5 = [d for d in diagnoses if d["status"] == "OK"][:5]
    metabolisms = []
    
    dry_run = not args.apply
    
    for d in top_5:
        target_file = PROJECT_ROOT / d["file"]
        logger.info("Metabolizing %s (entropy: %.2f)", d["file"], d["entropy"])
        try:
            omega = OuroborosOmega(
                target_path=str(target_file),
                project_root=str(PROJECT_ROOT),
                dry_run=dry_run
            )
            res = await omega.execute_atomic_cycle()
            metabolisms.append({
                "file": d["file"],
                "status": res.get("status"),
                "delta": res.get("delta", 0.0),
                "new_code": res.get("new_code") if dry_run else None
            })
        except Exception as e:
            logger.error("Error metabolizing %s: %s", d["file"], e)
            metabolisms.append({
                "file": d["file"],
                "status": "ERROR",
                "error": f"{type(e).__name__}: {str(e)}",
                "delta": 0.0,
                "new_code": None
            })
            
    # 4. GATE — Run OuroborosGate entropy measurement on CORTEX DB
    gate_metrics = {}
    dead_weight = None
    try:
        engine = get_engine()
        gate = OuroborosGate(engine._get_sync_conn())
        gate_metrics = gate.measure_entropy()
        dead_weight = gate.identify_dead_weight()
        if dead_weight:
            logger.info("Found dead weight candidate: %s", dead_weight)
    except Exception as e:
        logger.error("Error running OuroborosGate: %s", e)
        gate_metrics = {
            "error": str(e)
        }

    # Calculate accumulator_root
    accumulator_root = None
    try:
        import cortex_rs
        acc = cortex_rs.OuroborosStateAccumulator()
        for i, item in enumerate(diagnoses):
            acc.append_state(item["file"], json.dumps({"entropy": item["entropy"]}))
        accumulator_root = acc.get_root()
    except Exception as e:
        logger.warning("Could not calculate accumulator root using cortex_rs: %s", e)
        import hashlib
        payload = "".join(f"{item['file']}:{item['entropy']}" for item in diagnoses)
        accumulator_root = hashlib.sha256(payload.encode()).hexdigest()

    elapsed = round(time.perf_counter() - start_time, 2)
    
    # Compile summary stats
    files_scanned = len(python_files)
    files_ok = sum(1 for d in diagnoses if d["status"] == "OK")
    files_error = len(errors)
    avg_entropy = round(sum(d["entropy"] for d in diagnoses if d["status"] == "OK") / max(1, files_ok), 2)
    total_blocking = sum(len(d["blocking_calls"]) for d in diagnoses)
    total_dead = sum(len(d["dead_interfaces"]) for d in diagnoses)
    total_unused = sum(len(d["unused_imports"]) for d in diagnoses)
    
    report = {
        "timestamp": utc_now.isoformat(),
        "elapsed_seconds": elapsed,
        "summary": {
            "files_scanned": files_scanned,
            "files_ok": files_ok,
            "files_error": files_error,
            "avg_entropy": avg_entropy,
            "total_blocking_calls": total_blocking,
            "total_dead_interfaces": total_dead,
            "total_unused_imports": total_unused
        },
        "top_entropy": diagnoses[:20],
        "errors": errors,
        "metabolisms": metabolisms,
        "gate": {
            "status": "OK",
            "entropy_metrics": gate_metrics,
            "dead_weight_candidate": dead_weight,
            "accumulator_root": accumulator_root
        }
    }
    
    # Save daily report
    report_dir = PROJECT_ROOT / ".scratch" / "ouroboros" / "daily_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"ouroboros_{utc_now.date().isoformat()}.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    logger.info("Daily report written to %s", report_file)
    print(json.dumps({
        "status": "COMPLETE",
        "report_file": str(report_file),
        "files_scanned": files_scanned,
        "avg_entropy": avg_entropy,
        "metabolized": [m["file"] for m in metabolisms]
    }, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
