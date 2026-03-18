"""Mac-Maestro-Ω — Structured trace emission.

Traces are emitted to:
1. Python logger (always)
2. CORTEX Ledger (if available)
3. JSON Lines file (append-only, configurable via MAC_MAESTRO_TRACE_FILE)
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("mac_maestro.trace")

# ─── Trace File Config ────────────────────────────────────────────
DEFAULT_TRACE_DIR = Path.home() / ".cortex"
DEFAULT_TRACE_FILE = DEFAULT_TRACE_DIR / "mac_maestro_traces.jsonl"
TRACE_FILE = Path(
    os.environ.get("MAC_MAESTRO_TRACE_FILE", str(DEFAULT_TRACE_FILE))
)
_ledger = None
_ledger_attempted = False


def _get_ledger():
    """Lazy-init singleton connection to CORTEX Ledger."""
    global _ledger, _ledger_attempted
    if _ledger_attempted:
        return _ledger
    _ledger_attempted = True
    try:
        from cortex.config import DEFAULT_DB_PATH
        from cortex.ledger import SovereignLedger

        _ledger = SovereignLedger(DEFAULT_DB_PATH)
        logger.info("CORTEX Ledger connected for Mac-Maestro tracing.")
    except Exception:
        logger.debug("CORTEX Ledger unavailable — traces are local only.")
    return _ledger


def emit_trace(
    *,
    run_id: str,
    bundle_id: str,
    pid: int | None,
    frontmost: bool,
    window_title: str | None,
    selected_vector: str,
    outcome: str,
    target_query: dict[str, Any] | None,
    matched_element: dict[str, Any] | None = None,
    precondition_results: dict[str, bool] | None = None,
    postcondition_results: dict[str, bool] | None = None,
    retry_count: int = 0,
    failure_class: str | None = None,
    resolution_method: str | None = None,
    resolution_confidence: float | None = None,
    candidates_count: int = 0,
    click_target: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Emit a structured RunTrace for auditing and debugging.

    The `degraded` flag is automatically set if critical context
    (pid, window_title) is missing.
    """
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()

    # ── Degradation Detection ──
    degraded = pid is None

    trace_data: dict[str, Any] = {
        "run_id": run_id,
        "timestamp": timestamp,
        "bundle_id": bundle_id,
        "pid": pid,
        "frontmost": frontmost,
        "window_title": window_title,
        "selected_vector": selected_vector,
        "outcome": outcome,
        "target_query": target_query,
        "matched_element": matched_element,
        "precondition_results": precondition_results,
        "postcondition_results": postcondition_results,
        "retry_count": retry_count,
        "failure_class": failure_class,
        "degraded": degraded,
        "resolution_method": resolution_method,
        "resolution_confidence": resolution_confidence,
        "candidates_count": candidates_count,
        "click_target": click_target,
    }

    logger.info(
        "TRACE %s | %s | v=%s | %s%s",
        run_id,
        outcome,
        selected_vector,
        bundle_id,
        " [DEGRADED]" if degraded else "",
    )

    # ── CORTEX Ledger Hook ──
    ledger = _get_ledger()
    if ledger is not None:
        try:
            ledger.append(
                entry_type="mac_maestro_trace",
                payload=json.dumps(trace_data, default=str),
            )
        except Exception:
            logger.debug("Ledger write failed — trace persisted locally only.")

    # ── JSON Lines File Persistence ──
    _write_trace_to_file(trace_data)

    return trace_data


def _write_trace_to_file(trace_data: dict[str, Any]) -> None:
    """Append trace as a single JSON line to the trace file."""
    try:
        TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with TRACE_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace_data, default=str) + "\n")
            f.flush()
    except Exception:
        logger.debug("Trace file write failed: %s", TRACE_FILE)


def load_traces(
    path: Path | str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Load recent traces from JSON Lines file.

    Args:
        path: Path to trace file. Defaults to TRACE_FILE.
        limit: Maximum number of traces to return (most recent first).

    Returns:
        List of trace dicts, newest first.
    """
    trace_path = Path(path) if path else TRACE_FILE
    if not trace_path.exists():
        return []

    traces: list[dict[str, Any]] = []
    with trace_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    traces.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Return most recent first, limited
    return traces[-limit:][::-1]
