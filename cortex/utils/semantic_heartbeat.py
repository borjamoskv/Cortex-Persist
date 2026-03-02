"""
Semantic Heartbeat — Metastatic Drift Analysis.

A true heartbeat monitor calculating the semantic asymmetry
between system health states.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger("cortex.heartbeat.semantic")


class SemanticHeartbeat:
    """Calculates the metastate drift of system hygiene."""

    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold
        self.last_entropy_hash = ""
        self.last_report: dict[str, Any] = {}

    def _hash_payload(self, payload: dict[str, Any]) -> str:
        """Serializes and hashes the health report."""
        # Normalize: round floats to 1 decimal to avoid jitter
        normalized = {
            k: round(v, 1) if isinstance(v, float) else v
            for k, v in payload.items()
        }
        # Handle load_average tuple
        if "load_average" in normalized:
            normalized["load_average"] = [round(x, 1) for x in normalized["load_average"]]

        dump = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(dump.encode()).hexdigest()

    def calculate_drift(self, current_report: dict[str, Any]) -> float:
        """
        Calculates the semantic drift (asymmetry) between states.

        Returns a float [0.0, 1.0].
        """
        current_hash = self._hash_payload(current_report)
        if not self.last_entropy_hash:
            self.last_entropy_hash = current_hash
            self.last_report = current_report
            return 0.0

        if current_hash == self.last_entropy_hash:
            return 0.0

        # Simple Hamming distance between hashes as proxy for asymmetry
        diff = sum(c1 != c2 for c1, c2 in zip(current_hash, self.last_entropy_hash, strict=False))
        drift = diff / len(current_hash)

        # High-weight semantic triggers: if orphans appeared, bypass hash and spike drift
        if current_report.get("orphans", 0) > self.last_report.get("orphans", 0):
            drift = max(drift, 0.9)  # CRITICAL DRIFT

        self.last_entropy_hash = current_hash
        self.last_report = current_report
        return drift
