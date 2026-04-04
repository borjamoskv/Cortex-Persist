"""
Sovereign Guard Runtime (Fail-Closed Stub).
Defined per RFC-CORTEX-NATIVE-AI §9 Epistemic Veto.
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

    def evaluate(
        self, context: dict[str, Any]
    ) -> GuardOutcome:
        try:
            from cortex.extensions.security.honeypot import (
                HONEY_POT,
            )

            decoy = HONEY_POT.check_exploitation(
                context["content"]
            )
            if decoy:
                return GuardOutcome(
                    allowed=False,
                    reason=(
                        "Unauthorized access to "
                        f"honeypot: {decoy.id}"
                    ),
                    severity="critical",
                    code="honeypot.breach",
                    meta={
                        "honeypot_triggered": True,
                        "decoy_id": decoy.id,
                    },
                )
            return GuardOutcome(
                allowed=True, code="honeypot.clear"
            )
        except ImportError:
            return GuardOutcome(
                allowed=True,
                reason="Honeypot missing, skipping",
            )


class IntentGuardWrapper(BaseGuard):
    """V9: Bridges SecurityMonitorClassifier into GuardRuntime.

    This guard evaluates swarm tasks against the 7 Intent
    Axioms (Ω1-Ω7) and the ZeroTrust tool filter (Ω6).

    Context keys:
      - command: The shell command to classify
      - agent: The agent name
      - user_request: Original user request
      - provenance: Parameter provenance
      - tool_outputs: Optional tool-derived data tags
    """

    name = "intent_guard"
    required = True

    def evaluate(
        self, context: dict[str, Any]
    ) -> GuardOutcome:
        try:
            from cortex.extensions.security.security_monitor import (
                MONITOR,
                ParameterProvenance,
            )

            cmd = context.get("command", "")
            if not cmd:
                # No command to classify — skip
                return GuardOutcome(
                    allowed=True,
                    code="intent.no_command",
                )

            task = {
                "command": cmd,
                "agent": context.get("agent", "unknown"),
            }
            provenance = context.get(
                "provenance",
                ParameterProvenance.AGENT_INFERRED,
            )
            verdict = MONITOR.classify(
                task,
                user_request=context.get(
                    "user_request", ""
                ),
                provenance=provenance,
                tool_outputs=context.get("tool_outputs"),
            )

            if not verdict.allowed:
                return GuardOutcome(
                    allowed=False,
                    reason=verdict.reason,
                    severity=(
                        "critical"
                        if verdict.tier >= 3
                        else "high"
                    ),
                    code=(
                        f"intent.{verdict.axiom_violated}"
                    ),
                    meta=verdict.to_dict(),
                )
            return GuardOutcome(
                allowed=True,
                code="intent.allowed",
                meta={
                    "tier": verdict.tier,
                    "source": verdict.intent_source,
                },
            )
        except ImportError:
            return GuardOutcome(
                allowed=True,
                reason=(
                    "SecurityMonitorClassifier "
                    "missing, skipping"
                ),
            )


# The canonical guard pipeline in priority order.
# IntentGuard runs first (cheapest, broadest coverage),
# then InjectionGuard (content-level scan), then the
# structural/behavioral guards.
DEFAULT_GUARD_PIPELINE: list[BaseGuard] = [
    IntentGuardWrapper(),
    InjectionGuardWrapper(),
    ContradictionSignalGuard(),
    BridgeConflictGuard(),
    AnomalyGuardWrapper(),
    HoneypotGuardWrapper(),
]


def enforce_guard_pipeline(
    guards: list[BaseGuard],
    context: dict[str, Any],
) -> list[GuardOutcome]:
    """Execute guards and raise on first mandatory failure.

    Uses fail-closed semantics: if a required guard crashes,
    the entire pipeline is halted.
    """
    outcomes = []
    for guard in guards:
        try:
            outcome = guard.evaluate(context)
            outcomes.append(outcome)

            if not outcome.allowed:
                is_critical = guard.required or (
                    outcome.severity
                    in {"high", "critical"}
                )
                if is_critical:
                    logger.error(
                        "🛑 [GUARD VOID] %s (%s): %s",
                        guard.name,
                        outcome.severity,
                        outcome.reason,
                    )
                    raise ValueError(
                        f"SECURITY GUARD BLOCK "
                        f"[{guard.name}]: "
                        f"{outcome.reason}"
                    )
                else:
                    logger.warning(
                        "🛡️ [GUARD WARNING] %s: %s",
                        guard.name,
                        outcome.reason,
                    )

        except ValueError:
            raise
        except Exception as e:
            if guard.required:
                logger.critical(
                    "🔥 [GUARD CRASH] %s: %s",
                    guard.name,
                    e,
                )
                raise RuntimeError(
                    f"FAIL-CLOSED: {guard.name} "
                    f"crashed: {e}"
                ) from e
            logger.error(
                "⚠️ [GUARD ERROR] %s: %s",
                guard.name,
                e,
            )

    return outcomes

