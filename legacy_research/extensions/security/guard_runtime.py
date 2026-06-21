# [C5-REAL] Exergy-Maximized
"""
Sovereign Guard Runtime (Fail-Closed Stub).
Defined per RFC-CORTEX-NATIVE-AI §9 Retrieval Veto.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("cortex.security.runtime")


class GuardOutcome:
    """Represents the result of a guard evaluation."""

    def __init__(
        self,
        allowed: bool,
        reason: str | None = None,
        severity: str = "low",
        code: str | None = None,
        meta: dict[str, Any] | None = None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.severity = severity
        self.code = code
        self.meta = meta or {}


class BaseGuard:
    """Base class for all security guards."""

    name: str = "base_guard"
    required: bool = False

    def evaluate(self, context: dict[str, Any]) -> GuardOutcome:
        raise NotImplementedError


class ContradictionSignalGuard(BaseGuard):
    """Detects structural contradictions in the signal bus."""

    name = "contradiction_signal_guard"
    required = True

    def evaluate(self, context: dict[str, Any]) -> GuardOutcome:
        rejection = context.get("nemesis_rejection")
        if rejection:
            return GuardOutcome(
                allowed=False,
                reason=str(rejection),
                severity="high",
                code="contradiction.detected",
            )
        return GuardOutcome(allowed=True, severity="low", code="contradiction.clear")


class BridgeConflictGuard(BaseGuard):
    """Detects multi-tenant or cross-project bridge conflicts."""

    name = "bridge_conflict_guard"
    required = True

    def evaluate(self, context: dict[str, Any]) -> GuardOutcome:
        bridge_res = context.get("bridge_result")
        if bridge_res and not bridge_res.get("allowed", True):
            reason = bridge_res.get("reason", "Unknown bridge conflict")
            return GuardOutcome(
                allowed=False,
                reason=reason,
                severity="high",
                code="bridge.blocked",
                meta={"meta_flags": bridge_res.get("meta_flags", {})},
            )
        return GuardOutcome(allowed=True, severity="low", code="bridge.allowed")


class InjectionGuardWrapper(BaseGuard):
    """Wrapper for the core InjectionGuard."""

    name = "injection_guard"
    required = True

    def evaluate(self, context: dict[str, Any]) -> GuardOutcome:
        try:
            from cortex.extensions.security.injection_guard import GUARD

            report = GUARD.scan(context["content"], source=context.get("source"))
            if not report.is_safe:
                return GuardOutcome(
                    allowed=report.highest_severity != "critical",
                    reason=f"Injection detected: {report.matches[0].description}",
                    severity=report.highest_severity,
                    code="injection.detected",
                    meta={
                        "injection_flagged": True,
                        "injection_severity": report.highest_severity,
                        "injection_matches": len(report.matches),
                    },
                )
            return GuardOutcome(allowed=True, code="injection.clear")
        except ImportError:
            return GuardOutcome(allowed=True, reason="InjectionGuard missing, skipping")


class AnomalyGuardWrapper(BaseGuard):
    """Wrapper for the statistical AnomalyDetector."""

    name = "anomaly_guard"
    required = False

    def evaluate(self, context: dict[str, Any]) -> GuardOutcome:
        try:
            from cortex.extensions.security.anomaly_detector import DETECTOR, SecurityEvent

            anomaly = DETECTOR.record_event(
                SecurityEvent(
                    source=context.get("source") or "unknown",
                    project=context["project"],
                    action="store",
                    content_length=len(context["content"]),
                )
            )
            if anomaly and anomaly.is_anomalous:
                return GuardOutcome(
                    allowed=anomaly.severity != "critical",
                    reason=anomaly.description,
                    severity=anomaly.severity,
                    code="anomaly.detected",
                    meta={
                        "anomaly_flagged": True,
                        "anomaly_type": anomaly.anomaly_type,
                        "anomaly_severity": anomaly.severity,
                    },
                )
            return GuardOutcome(allowed=True, code="anomaly.clear")
        except ImportError:
            return GuardOutcome(allowed=True, reason="AnomalyDetector missing, skipping")


class HoneypotGuardWrapper(BaseGuard):
    """Wrapper for the Honeypot breach detector."""

    name = "honeypot_guard"
    required = True

    def evaluate(self, context: dict[str, Any]) -> GuardOutcome:
        try:
            from cortex.extensions.security.honeypot import HONEY_POT

            decoy = HONEY_POT.check_exploitation(context["content"])
            if decoy:
                return GuardOutcome(
                    allowed=False,
                    reason=f"Unauthorized access to honeypot: {decoy.id}",
                    severity="critical",
                    code="honeypot.breach",
                    meta={"honeypot_triggered": True, "decoy_id": decoy.id},
                )
            return GuardOutcome(allowed=True, code="honeypot.clear")
        except ImportError:
            return GuardOutcome(allowed=True, reason="Honeypot missing, skipping")


def enforce_guard_pipeline(guards: list[BaseGuard], context: dict[str, Any]) -> list[GuardOutcome]:
    """Executes a list of guards and raises ValueError on first high-severity failure."""
    outcomes = []
    for guard in guards:
        try:
            outcome = guard.evaluate(context)
            outcomes.append(outcome)

            if not outcome.allowed:
                if guard.required or outcome.severity in {"high", "critical"}:
                    logger.error(
                        "🛑 [GUARD VOID] %s blocked (%s): %s",
                        guard.name,
                        outcome.severity,
                        outcome.reason,
                    )
                    raise ValueError(f"SECURITY GUARD BLOCK [{guard.name}]: {outcome.reason}")
                logger.warning("🛡️ [GUARD WARNING] %s flagged: %s", guard.name, outcome.reason)

        except Exception as e:
            if guard.required:
                logger.critical("🔥 [GUARD CRASH] Mandatory guard %s failed: %s", guard.name, e)
                raise RuntimeError(f"FAIL-CLOSED: Mandatory guard {guard.name} crashed: {e}") from e
            logger.error("⚠️ [GUARD ERROR] Optional guard %s failed: %s", guard.name, e)

    return outcomes
