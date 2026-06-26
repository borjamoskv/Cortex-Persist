# [C5-REAL] Exergy-Maximized
"""
Epistemic Dependency Graph (EDG) Metrics.

Deterministic aggregation of telemetry over the EDG.
Rejects click-tracking in favor of thermodynamic cognitive effort:
Resolution Time vs. Problem Cyclomatic Complexity.
"""

import hashlib
import json
import time
from typing import Any

from cortex.telemetry.metrics import metrics


class EDGTelemetryAggregator:
    """Aggregates thermodynamic cognitive effort and emits immutable hashes."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._history: list[dict[str, Any]] = []

    def record_effort(
        self, node_id: str, resolution_time_ms: int, cyclomatic_complexity: int, error_rate: float
    ) -> str:
        """
        Record a cognitive effort event.
        Calculates thermodynamic cost: (resolution_time_ms * error_rate) / complexity
        """
        # Exergy penalty calculation
        # If complexity is high, higher resolution time is expected.
        # If error rate is high, energy was lost to entropy (Anergy).

        effective_complexity = max(1, cyclomatic_complexity)
        thermodynamic_cost = (
            (resolution_time_ms / 1000.0) * (1.0 + error_rate) / effective_complexity
        )

        event = {
            "node_id": node_id,
            "tenant_id": self.tenant_id,
            "resolution_time_ms": resolution_time_ms,
            "complexity": cyclomatic_complexity,
            "error_rate": error_rate,
            "thermodynamic_cost": thermodynamic_cost,
            "timestamp": time.time(),
        }

        self._history.append(event)

        # Track in Prometheus registry
        metrics.observe(
            "cortex_edg_cognitive_effort_cost",
            thermodynamic_cost,
            labels={"tenant_id": self.tenant_id, "node_id": node_id},
        )

        return self._generate_ledger_hash(event)

    def _generate_ledger_hash(self, event: dict[str, Any]) -> str:
        """Produce an immutable hash of the student's progress for the Master Ledger."""
        payload = json.dumps(event, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get_progress_hash(self) -> str:
        """Returns the cumulative hash chain of all recorded effort."""
        chain_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        for event in self._history:
            combined = chain_hash + json.dumps(event, sort_keys=True)
            chain_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return chain_hash
