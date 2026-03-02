"""store_guards — Anti-Hacker Shield policies for the Store Layer.

Extracted from StoreMixin to satisfy the Landauer LOC barrier (≤500).
Each guard is an independent policy: ImportError → degrade gracefully.
ValueError → propagates for critical security blocks.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["run_security_guards"]

logger = logging.getLogger("cortex")


def _guard_injection(
    content: str,
    project: str,
    meta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Scan content for injection attacks."""
    try:
        from cortex.security.injection_guard import GUARD

        report = GUARD.scan(content)
        if not report.is_safe:
            logger.warning(
                "🛡️ INJECTION GUARD: %d threats (highest: %s) in [%s]",
                len(report.matches),
                report.highest_severity,
                project,
            )
            meta = {
                **(meta or {}),
                "injection_flagged": True,
                "injection_severity": report.highest_severity,
                "injection_matches": len(report.matches),
            }
            if report.highest_severity == "critical":
                raise ValueError(f"INJECTION BLOCKED: {report.matches[0].description}")
    except ImportError:
        pass  # Guard not installed — degrade gracefully
    return meta


def _guard_anomaly(
    content: str,
    project: str,
    source: str | None,
    meta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Check for statistical anomalies in store patterns."""
    try:
        from cortex.security.anomaly_detector import DETECTOR, SecurityEvent

        anomaly = DETECTOR.record_event(
            SecurityEvent(
                source=source or "unknown",
                project=project,
                action="store",
                content_length=len(content),
            )
        )
        if anomaly and anomaly.is_anomalous:
            logger.warning(
                "🔍 ANOMALY: %s (severity: %s, Z=%.1f) in [%s]",
                anomaly.anomaly_type,
                anomaly.severity,
                anomaly.z_score,
                project,
            )
            meta = {
                **(meta or {}),
                "anomaly_flagged": True,
                "anomaly_type": anomaly.anomaly_type,
                "anomaly_severity": anomaly.severity,
            }
            if anomaly.severity == "critical":
                from cortex.security.security_sync import SIGNAL

                SIGNAL.emit_sync("threat", {"type": "anomaly", "severity": "critical"})
                raise ValueError(f"ANOMALY BLOCKED: {anomaly.description}")
            if anomaly.severity == "high":
                from cortex.security.security_sync import SIGNAL

                SIGNAL.emit_sync("anomaly", {"type": "anomaly", "severity": "high"})
    except ImportError:
        pass  # Detector not installed — degrade gracefully
    return meta


def _guard_honeypot(
    content: str,
    meta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Check if content attempts to access a honeypot resource."""
    try:
        from cortex.security.honeypot import HONEY_POT
        from cortex.security.security_sync import SIGNAL

        decoy = HONEY_POT.check_exploitation(content)
        if decoy:
            SIGNAL.emit_sync("threat", {"type": "honeypot", "id": decoy.id})
            logger.critical("☢️ HONEYPOT BREACH: Unauthorized access to [%s]", decoy.id)
            meta = {
                **(meta or {}),
                "honeypot_triggered": True,
                "decoy_id": decoy.id,
            }
            raise ValueError(f"SECURITY BREACH: Unauthorized resource [{decoy.id}]")
    except ImportError:
        pass  # Honeypot not installed — degrade gracefully
    return meta


def run_security_guards(
    content: str,
    project: str,
    source: str | None,
    meta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Run all Anti-Hacker Shield guards (injection, anomaly, honeypot).

    Each guard is optional (ImportError → degrade gracefully).
    ValueError propagates for critical security blocks.

    Returns the (potentially enriched) metadata dict.
    """
    meta = _guard_injection(content, project, meta)
    meta = _guard_anomaly(content, project, source, meta)
    meta = _guard_honeypot(content, meta)
    return meta
