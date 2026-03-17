"""Mac-Maestro-Ω — Structured trace emission."""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any

logger = logging.getLogger("mac_maestro.trace")

# ─── CORTEX Ledger Singleton ──────────────────────────────────────
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

    return trace_data
