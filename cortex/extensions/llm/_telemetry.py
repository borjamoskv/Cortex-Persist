from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Optional

from cortex.database.core import connect as db_connect
from cortex.extensions.llm._models import CascadeEvent, CascadeTier

logger = logging.getLogger("cortex.extensions.llm.telemetry")


class CascadeTelemetry:
    """Manages the structured logs and stats for cascade execution.

    Axiom: Ω₄ Aesthetic Integrity (visualizing entropy) + Ω₃ Byzantine
           Grounding (tracing failures).
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.events: list[CascadeEvent] = []
        self._db_path = db_path

    def emit(self, event: CascadeEvent) -> None:
        """Record structured telemetry for this cascade resolution."""
        # Truncate history to prevent memory leaks (sliding window)
        if len(self.events) >= 1000:
            self.events.pop(0)

        self.events.append(event)

        # Log visual forensic summary
        msg = f"Cascade: intent={event.intent.value} | res={event.resolved_by or 'FAIL'}"
        msg += f" | tier={event.tier.value} | depth={event.depth} | lat={event.latency_ms:.1f}ms"

        if not event.resolved_by:
            logger.error("Ω₃ Byzantine Failure: %s | errors=%s", msg, event.errors)
        elif event.tier == CascadeTier.SAFETY_NET:
            logger.warning("Ω₄ Entropy Elevated (Safety-Net Active): %s", msg)
        else:
            logger.info("Ω₃ Byzantine Validated: %s", msg)

        if self._db_path:
            self._persist_to_db(event)

    def _persist_to_db(self, event: CascadeEvent) -> None:
        """Sovereign Persistence (Ω₃): Drive telemetry to the physical ledger."""
        try:
            conn = db_connect(self._db_path)  # type: ignore[type-error]
            try:
                conn.execute(
                    "INSERT INTO llm_telemetry "
                    "(intent, resolved_by, project, tier, depth, latency_ms, errors, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event.intent.value,
                        event.resolved_by,
                        event.project,
                        event.tier.value,
                        event.depth,
                        event.latency_ms,
                        json.dumps(event.errors),
                        event.timestamp,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except (sqlite3.Error, OSError) as e:
            logger.warning("Ω₄ Persistence Stall: Could not write LLM telemetry: %s", e)

    def stats(self) -> dict[str, Any]:
        """Aggregate cascade metrics across the sliding window."""
        counts = {t.value: 0 for t in CascadeTier}
        latencies: list[float] = []
        total = len(self.events)

        if not total:
            return {
                "total": 0,
                "breakdown": counts,
                "avg_latency_ms": 0.0,
                "success_rate": 0.0,
                "entropy_elevation_count": 0,
            }

        entropy_inc = 0
        successes = 0

        for ev in self.events:
            if ev.resolved_by:
                successes += 1
                counts[ev.tier.value] += 1
                latencies.append(ev.latency_ms)
                if ev.tier == CascadeTier.SAFETY_NET:
                    entropy_inc += 1

        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

        return {
            "total": total,
            "successes": successes,
            "success_rate": round(successes / total, 3),
            "avg_latency_ms": round(avg_lat, 2),
            "breakdown": counts,
            "entropy_elevation_count": entropy_inc,
            "reliability_index": round((successes - entropy_inc) / total, 3) if total else 0.0,
        }
