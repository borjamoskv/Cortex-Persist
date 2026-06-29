#!/usr/bin/env python3
"""
control_plane.py

Cortex Control Plane — Autonomous Scheduler
============================================

Author: Borja Moskv / borjamoskv

Closes the heartbeat:
    read feedback -> run reality_cycle -> dispatch job -> run swarm worker -> persist -> repeat

Compatible with the async reality_loop.py (DistributedEventBus).
No external dependencies beyond stdlib + local modules.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Paths
# =============================================================================

ROOT = Path(__file__).resolve().parent

RUNTIME_DIR = ROOT / "runtime"
CONTROL_STATE_PATH = RUNTIME_DIR / "control_plane_state.json"
CONTROL_EVENT_LOG_PATH = RUNTIME_DIR / "control_plane_events.jsonl"
LOCK_PATH = RUNTIME_DIR / "control_plane.lock"

LOCAL_FEEDBACK_DIR = RUNTIME_DIR / "swarm_feedback"

MOSKV_SWARM_ROOT = ROOT.parent / "moskv-swarm"
MOSKV_SWARM_WORKER = MOSKV_SWARM_ROOT / "swarm_worker.py"
MOSKV_SWARM_FEEDBACK_DIR = MOSKV_SWARM_ROOT / "feedback"


# =============================================================================
# Defaults
# =============================================================================

DEFAULT_BOOTSTRAP_METRIC = {
    "originality_ratio": 0.5,
    "distribution_yield": 0.5,
    "entropy": 0.6,
    "coherence": 0.5,
    "fatigue": 0.0,
}


DEFAULT_CONTROL_STATE = {
    "started_at": None,
    "cycle_count": 0,
    "last_cycle_at": None,
    "last_metric_source": None,
    "last_metric": None,
    "last_feedback_id": None,
    "last_feedback_path": None,
    "consumed_feedback_ids": [],
    "last_reality_result": None,
    "last_worker_result": None,
    "error_count": 0,
    "last_error": None,
}


# =============================================================================
# Utilities
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clone_default(value: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(value))


def ensure_dirs() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

    if MOSKV_SWARM_ROOT.exists():
        MOSKV_SWARM_FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    base = clone_default(default or {})

    if not path.exists():
        return base

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            base.update(data)

        return base

    except Exception:
        return base


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_jsonl(path: Path, item: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def emit_event(event_type: str, payload: Dict[str, Any]) -> None:
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": utc_now(),
        "source": "control_plane",
        "event_type": event_type,
        "payload": payload,
    }

    append_jsonl(CONTROL_EVENT_LOG_PATH, event)


def clamp01(value: Any, default: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = default

    if not math.isfinite(v):
        v = default

    return round(max(0.0, min(1.0, v)), 3)


def normalize_metric(metric: Dict[str, Any]) -> Dict[str, float]:
    return {
        key: clamp01(metric.get(key, default), default)
        for key, default in DEFAULT_BOOTSTRAP_METRIC.items()
    }


def timestamp_sort_value(timestamp: Any, fallback: float) -> float:
    if isinstance(timestamp, str) and timestamp:
        try:
            return datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            ).timestamp()
        except Exception:
            pass

    return fallback


def trim_text(text: Optional[str], limit: int = 3000) -> str:
    if not text:
        return ""

    if len(text) <= limit:
        return text

    return text[-limit:]


# =============================================================================
# Lock
# =============================================================================

class ControlPlaneLock:
    def __init__(self, path: Path, force: bool = False):
        self.path = path
        self.force = force
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.force and self.path.exists():
            self.path.unlink(missing_ok=True)

        try:
            fd = os.open(
                str(self.path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "pid": os.getpid(),
                    "timestamp": utc_now(),
                }, indent=2))

            self.acquired = True

        except FileExistsError:
            existing = ""

            try:
                existing = self.path.read_text(encoding="utf-8")
            except Exception:
                pass

            raise RuntimeError(
                "Control Plane is already locked.\n"
                f"Lock file: {self.path}\n"
                f"Existing lock content: {existing}\n"
                "If this is stale, rerun with --force-lock."
            )

    def release(self) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False

    def __enter__(self) -> "ControlPlaneLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


# =============================================================================
# Feedback Ingestion
# =============================================================================

def feedback_dirs() -> List[Path]:
    dirs = [LOCAL_FEEDBACK_DIR]

    if MOSKV_SWARM_FEEDBACK_DIR.exists():
        dirs.append(MOSKV_SWARM_FEEDBACK_DIR)

    return dirs


def path_priority(path: Path) -> int:
    """
    Prefer cortex-system/runtime/swarm_feedback over moskv-swarm/feedback.
    """
    try:
        path.resolve().relative_to(LOCAL_FEEDBACK_DIR.resolve())
        return 0
    except Exception:
        return 1


def discover_feedback_records(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    consumed = set(str(x) for x in state.get("consumed_feedback_ids", []))
    records_by_id: Dict[str, Dict[str, Any]] = {}

    for directory in feedback_dirs():
        if not directory.exists():
            continue

        for path in sorted(directory.glob("feedback_*.json")):
            data = load_json(path, {})

            metrics = data.get("estimated_metrics")
            if not isinstance(metrics, dict):
                continue

            feedback_id = str(
                data.get("feedback_id")
                or data.get("job_id")
                or path.resolve()
            )

            if feedback_id in consumed:
                continue

            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = time.time()

            record = {
                "feedback_id": feedback_id,
                "job_id": data.get("job_id"),
                "path": str(path),
                "metrics": metrics,
                "timestamp": data.get("timestamp"),
                "artifact_status": data.get("artifact_status"),
                "rejection_reason": data.get("rejection_reason"),
                "sort_value": timestamp_sort_value(data.get("timestamp"), mtime),
                "priority": path_priority(path),
            }

            existing = records_by_id.get(feedback_id)

            if existing is None or record["priority"] < existing["priority"]:
                records_by_id[feedback_id] = record

    return sorted(
        records_by_id.values(),
        key=lambda r: (r["sort_value"], r["feedback_id"]),
    )


def select_metric(
    state: Dict[str, Any],
    bootstrap_metric: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Priority:
        1. Oldest unconsumed swarm feedback.
        2. Bootstrap metric.
    """
    records = discover_feedback_records(state)

    if records:
        record = records[0]

        return {
            "source": "feedback",
            "metric": normalize_metric(record["metrics"]),
            "feedback_id": record["feedback_id"],
            "feedback_path": record["path"],
            "job_id": record.get("job_id"),
            "artifact_status": record.get("artifact_status"),
            "rejection_reason": record.get("rejection_reason"),
        }

    return {
        "source": "bootstrap",
        "metric": normalize_metric(bootstrap_metric),
        "feedback_id": None,
        "feedback_path": None,
        "job_id": None,
        "artifact_status": None,
        "rejection_reason": None,
    }


def mark_feedback_consumed(state: Dict[str, Any], feedback_id: Optional[str]) -> None:
    if not feedback_id:
        return

    consumed = [str(x) for x in state.get("consumed_feedback_ids", [])]

    if feedback_id not in consumed:
        consumed.append(feedback_id)

    # Keep state bounded.
    state["consumed_feedback_ids"] = consumed[-500:]


# =============================================================================
# Cortex Reality Loop Bridge (async)
# =============================================================================

def run_reality(metric: Dict[str, Any]) -> Dict[str, Any]:
    """
    Import and execute cortex-system/reality_loop.py.
    Bridges async run_reality_cycle into sync caller via asyncio.run().
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        from reality_loop import run_reality_cycle
        from babylon60.events.bus import DistributedEventBus
    except Exception as e:
        raise RuntimeError(
            "Could not import run_reality_cycle or DistributedEventBus. "
            "Ensure cortex-system/reality_loop.py and babylon60 exist."
        ) from e

    bus = DistributedEventBus()
    return asyncio.run(run_reality_cycle(metric, bus))


def summarize_reality_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": result.get("ok"),
        "event_id": result.get("event_id"),
        "decision": result.get("decision"),
        "action": result.get("action"),
        "job_path": result.get("job_path"),
    }


# =============================================================================
# Swarm Worker Bridge
# =============================================================================

def run_swarm_worker_once(
    worker_mode: str,
    timeout: float,
) -> Dict[str, Any]:
    """
    worker_mode:
        integrated: Run moskv-swarm/swarm_worker.py once after every Cortex cycle.
        external:   Assume swarm_worker.py is running in another terminal.
        off:        Do not run worker.
    """
    if worker_mode == "off":
        return {"mode": worker_mode, "ok": True, "skipped": True, "reason": "worker_disabled"}

    if worker_mode == "external":
        return {"mode": worker_mode, "ok": True, "skipped": True, "reason": "external_worker_expected"}

    if not MOSKV_SWARM_WORKER.exists():
        return {
            "mode": worker_mode,
            "ok": False,
            "skipped": True,
            "reason": f"swarm_worker_not_found: {MOSKV_SWARM_WORKER}",
        }

    started = time.time()

    try:
        proc = subprocess.run(
            [sys.executable, str(MOSKV_SWARM_WORKER)],
            cwd=str(MOSKV_SWARM_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "mode": worker_mode,
            "ok": proc.returncode == 0,
            "skipped": False,
            "returncode": proc.returncode,
            "duration_sec": round(time.time() - started, 3),
            "stdout": trim_text(proc.stdout),
            "stderr": trim_text(proc.stderr),
        }

    except subprocess.TimeoutExpired as e:
        return {
            "mode": worker_mode,
            "ok": False,
            "skipped": False,
            "timeout": True,
            "duration_sec": round(time.time() - started, 3),
            "stdout": trim_text(
                e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout
            ),
            "stderr": trim_text(
                e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr
            ),
        }


# =============================================================================
# Control Cycle
# =============================================================================

def run_control_cycle(
    args: argparse.Namespace,
    bootstrap_metric: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    state = load_json(CONTROL_STATE_PATH, DEFAULT_CONTROL_STATE)

    if not state.get("started_at"):
        state["started_at"] = utc_now()

    metric_packet = select_metric(state, bootstrap_metric)
    next_cycle = int(state.get("cycle_count", 0)) + 1

    emit_event(
        "cycle_started",
        {
            "cycle": next_cycle,
            "metric_source": metric_packet["source"],
            "feedback_id": metric_packet.get("feedback_id"),
            "metric": metric_packet["metric"],
        },
    )

    try:
        reality_result = run_reality(metric_packet["metric"])
        reality_summary = summarize_reality_result(reality_result)

        if metric_packet["source"] == "feedback":
            mark_feedback_consumed(state, metric_packet.get("feedback_id"))

        worker_result = run_swarm_worker_once(
            worker_mode=args.worker_mode,
            timeout=args.worker_timeout,
        )

        state["cycle_count"] = next_cycle
        state["last_cycle_at"] = utc_now()
        state["last_metric_source"] = metric_packet["source"]
        state["last_metric"] = metric_packet["metric"]
        state["last_feedback_id"] = metric_packet.get("feedback_id")
        state["last_feedback_path"] = metric_packet.get("feedback_path")
        state["last_reality_result"] = reality_summary
        state["last_worker_result"] = worker_result
        state["last_error"] = None

        save_json(CONTROL_STATE_PATH, state)

        summary = {
            "ok": True,
            "cycle": next_cycle,
            "metric_source": metric_packet["source"],
            "feedback_id": metric_packet.get("feedback_id"),
            "decision": reality_summary.get("decision"),
            "action": reality_summary.get("action"),
            "job_path": reality_summary.get("job_path"),
            "worker": {
                "mode": worker_result.get("mode"),
                "ok": worker_result.get("ok"),
                "skipped": worker_result.get("skipped"),
                "returncode": worker_result.get("returncode"),
                "reason": worker_result.get("reason"),
            },
        }

        emit_event("cycle_completed", summary)

        return state, summary

    except Exception as e:
        error_payload = {
            "timestamp": utc_now(),
            "cycle": next_cycle,
            "error_type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc(),
        }

        state["error_count"] = int(state.get("error_count", 0)) + 1
        state["last_error"] = error_payload

        save_json(CONTROL_STATE_PATH, state)
        emit_event("cycle_failed", error_payload)

        if args.stop_on_error:
            raise

        return state, {"ok": False, "cycle": next_cycle, "error": error_payload}


# =============================================================================
# CLI
# =============================================================================

def load_bootstrap_metric(args: argparse.Namespace) -> Dict[str, Any]:
    if args.bootstrap_metric_file:
        path = Path(args.bootstrap_metric_file)

        if not path.exists():
            raise FileNotFoundError(f"Bootstrap metric file not found: {path}")

        return normalize_metric(load_json(path, DEFAULT_BOOTSTRAP_METRIC))

    return normalize_metric({
        "originality_ratio": args.bootstrap_originality_ratio,
        "distribution_yield": args.bootstrap_distribution_yield,
        "entropy": args.bootstrap_entropy,
        "coherence": args.bootstrap_coherence,
        "fatigue": args.bootstrap_fatigue,
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cortex Control Plane autonomous scheduler."
    )

    parser.add_argument(
        "--daemon", action="store_true",
        help="Run continuously. Without this flag, runs one cycle.",
    )
    parser.add_argument(
        "--interval", type=float, default=30.0,
        help="Seconds between cycles in daemon mode.",
    )
    parser.add_argument(
        "--max-cycles", type=int, default=0,
        help="Maximum cycles in daemon mode. 0 = infinite.",
    )
    parser.add_argument(
        "--worker-mode", choices=["integrated", "external", "off"],
        default="integrated",
        help="integrated = run swarm_worker.py once per cycle; "
             "external = assume worker daemon is running; off = skip.",
    )
    parser.add_argument(
        "--worker-timeout", type=float, default=120.0,
        help="Timeout for integrated swarm worker execution.",
    )
    parser.add_argument(
        "--force-lock", action="store_true",
        help="Remove stale lock and start anyway.",
    )
    parser.add_argument(
        "--stop-on-error", action="store_true",
        help="Stop daemon if one cycle fails.",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Do not print cycle summaries.",
    )
    parser.add_argument(
        "--bootstrap-metric-file", type=str, default=None,
        help="Optional JSON file used when no feedback exists.",
    )
    parser.add_argument("--bootstrap-originality-ratio", type=float, default=0.5)
    parser.add_argument("--bootstrap-distribution-yield", type=float, default=0.5)
    parser.add_argument("--bootstrap-entropy", type=float, default=0.6)
    parser.add_argument("--bootstrap-coherence", type=float, default=0.5)
    parser.add_argument("--bootstrap-fatigue", type=float, default=0.0)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    ensure_dirs()
    bootstrap_metric = load_bootstrap_metric(args)

    with ControlPlaneLock(LOCK_PATH, force=args.force_lock):
        executed = 0

        while True:
            _, summary = run_control_cycle(args, bootstrap_metric)
            executed += 1

            if not args.quiet:
                print(json.dumps(summary, indent=2, ensure_ascii=False))

            if not args.daemon:
                break

            if 0 < args.max_cycles <= executed:
                break

            time.sleep(max(0.0, args.interval))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[control_plane] stopped by user", file=sys.stderr)
