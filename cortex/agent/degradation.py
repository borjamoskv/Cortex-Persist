"""
CORTEX v7 — Sovereign Degradation Protocol (Ω₅ Applied).

Materializes §14 of AGENTICA.md: "Degradación Soberana — Ω₅ Aplicado a Sistemas Agénticos".

Philosophy:
  Robustness is not measured by the absence of failures, but by the
  informational quality of the failure when it occurs.

  L0 — Hard Crash  : Silent termination. Pure entropy.
  L1 — Opaque Error: Generic message. No recovery path.
  L2 — Informed    : Cause identified. No action suggested.
  L3 — Actionable  : Cause + recovery path + alternatives.  ← Sovereign minimum
  L4 — Graceful    : Operates at reduced capacity, notifies limits. ← Antifragile

CORTEX targets L3–L4. An agent that fails silently is not broken — it is incomplete.

Axiom derivation: Ω₅ (Antifragile by Default) — Error = gradient.
A failure that produces no information produces no gradient.
Without gradient, no learning. Without learning, the system calcifies.

Usage::

    from cortex.agent.degradation import (
        AgentAction,
        AgentResult,
        AgentDegradedError,
        SchemaIncompatibilityError,
        sovereign_execute,
    )

    class MyAgent:
        @sovereign_execute(fallback_mode="text_only")
        async def execute(self, action: AgentAction) -> AgentResult:
            ...
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    # Exception hierarchy
    "SovereignAgentError",
    "SchemaIncompatibilityError",
    "ToolRegistrationError",
    "ModelUnavailableError",
    "AgentDegradedError",
    "AgentCalcificationError",
    # Data contracts
    "DegradationLevel",
    "AgentAction",
    "AgentResult",
    "DegradationReport",
    # Decorator
    "sovereign_execute",
]

logger = logging.getLogger("cortex.agent.degradation")

_RECOVERY_DOCTOR = "Run `cortex doctor` to scan subsystem health"  # shared recovery step


# ─── Degradation Level Taxonomy ──────────────────────────────────────────────


class DegradationLevel(int, Enum):
    """Informational quality of a failure (AGENTICA §14).

    Higher = more antifragile.
    CORTEX sovereign standard: L3 or above.
    """

    L0_HARD_CRASH = 0  # Silent termination. Pure entropy.
    L1_OPAQUE_ERROR = 1  # Generic message. No recovery path.
    L2_INFORMED = 2  # Cause identified. No action suggested.
    L3_ACTIONABLE = 3  # Cause + recovery path + alternatives.
    L4_GRACEFUL = 4  # Operates at reduced capacity, notifies limits.

    @property
    def is_sovereign(self) -> bool:
        """True if meets the sovereign minimum (L3+)."""
        return self >= DegradationLevel.L3_ACTIONABLE

    @property
    def symbol(self) -> str:
        return ["☠️", "❌", "🟡", "✅", "💎"][self.value]


# ─── Exception Hierarchy ─────────────────────────────────────────────────────


class SovereignAgentError(Exception):
    """Base exception for all CORTEX agent failures.

    All subclasses MUST provide:
      - component    : which subsystem failed
      - recovery_steps: ordered list of suggested remediation actions
      - suggested_alt : alternative component/model/path (optional)
    """

    level: DegradationLevel = DegradationLevel.L3_ACTIONABLE

    def __init__(
        self,
        message: str,
        *,
        component: str,
        recovery_steps: list[str],
        suggested_alt: str | None = None,
        cause: BaseException | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.component = component
        self.recovery_steps = recovery_steps
        self.suggested_alt = suggested_alt
        self.cause = cause
        self.context = context or {}
        self.timestamp = time.time()

    def as_report(self) -> DegradationReport:
        return DegradationReport(
            level=self.level,
            component=self.component,
            message=str(self),
            recovery_steps=self.recovery_steps,
            suggested_alt=self.suggested_alt,
            context=self.context,
            timestamp=self.timestamp,
        )

    def __str__(self) -> str:
        parts = [super().__str__()]
        parts.append(f"component={self.component}")
        if self.suggested_alt:
            parts.append(f"suggested={self.suggested_alt}")
        if self.recovery_steps:
            steps = " | ".join(self.recovery_steps)
            parts.append(f"recovery=[{steps}]")
        return " | ".join(parts)


class SchemaIncompatibilityError(SovereignAgentError):
    """Model does not support the required function-calling schema.

    L3 — Actionable: cause identified, alternative model suggested.
    """

    level = DegradationLevel.L3_ACTIONABLE

    def __init__(
        self,
        *,
        model: str,
        required_schema: str,
        actual_schema: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self._model = model
        super().__init__(
            f"Model '{model}' does not support schema '{required_schema}'",
            component="tool_registration",
            recovery_steps=[
                "Switch to a model with native function-calling support (gemini-2.0+)",
                "Use text-only inference mode (--no-tools flag)",
                "Downgrade to a compatible schema version",
            ],
            suggested_alt="gemini-2.0-flash",
            cause=cause,
            context={
                "model": model,
                "required_schema": required_schema,
                "actual_schema": actual_schema,
            },
        )


class ToolRegistrationError(SovereignAgentError):
    """Tool registration failed — tool not available or misconfigured."""

    level = DegradationLevel.L3_ACTIONABLE

    def __init__(self, *, tool_name: str, cause: BaseException | None = None) -> None:
        super().__init__(
            f"Tool '{tool_name}' failed to register",
            component="tool_registry",
            recovery_steps=[
                f"Check tool '{tool_name}' is installed and in PATH",
                "Run `cortex doctor` to diagnose tool availability",
                "Disable the tool via role.yaml and retry",
            ],
            suggested_alt=None,
            cause=cause,
            context={"tool_name": tool_name},
        )


class ModelUnavailableError(SovereignAgentError):
    """Target model is unavailable (quota, network, version)."""

    level = DegradationLevel.L3_ACTIONABLE

    def __init__(
        self,
        *,
        model: str,
        reason: str,
        fallback_model: str = "gemini-2.0-flash",
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            f"Model '{model}' unavailable: {reason}",
            component="model_client",
            recovery_steps=[
                f"Switch to fallback model: {fallback_model}",
                "Check API key and quota in `cortex status`",
                "Retry after rate-limit window (usually 60s)",
            ],
            suggested_alt=fallback_model,
            cause=cause,
            context={"model": model, "reason": reason},
        )


class AgentDegradedError(SovereignAgentError):
    """Agent is operating in a degraded mode after a partial failure.

    Raised when neither full execution nor text-only fallback is viable.
    Always L3 — carries full context for the user to take action.
    """

    level = DegradationLevel.L3_ACTIONABLE

    def __init__(
        self,
        *,
        cause: BaseException,
        component: str,
        suggested_model: str | None = None,
        recovery_steps: list[str] | None = None,
    ) -> None:
        super().__init__(
            f"Agent degraded after failure in {component}: {cause}",
            component=component,
            recovery_steps=recovery_steps
            or [
                "Check component logs for root cause",
                _RECOVERY_DOCTOR,
                (
                    f"Switch to: {suggested_model}"
                    if suggested_model
                    else "Restart with reduced toolset"
                ),
            ],
            suggested_alt=suggested_model,
            cause=cause,
            context={"original_error": type(cause).__name__},
        )


class AgentCalcificationError(SovereignAgentError):
    """Agent has stopped evolving — δ≈0 detected (Ω₅ violation).

    Raised when the system detects the agent is repeating the same
    failure pattern without generating new learning gradient.
    Calcification is the systemic death state under Ω₅.
    """

    level = DegradationLevel.L2_INFORMED

    def __init__(self, *, failure_count: int, pattern: str) -> None:
        super().__init__(
            f"Calcification detected: same failure '{pattern}' repeated {failure_count}x "
            f"without recovery learning (δ≈0)",
            component="meta_monitor",
            recovery_steps=[
                "Store failure pattern in CORTEX: `cortex store --type error ...`",
                "Force architectural mutation: try a different approach",
                "Invoke Trampolin protocol for auto-evolutionary recovery",
            ],
            context={"failure_count": failure_count, "pattern": pattern},
        )


# ─── Data Contracts ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class AgentAction:
    """An action request to an agent (input contract).

    Immutable — never mutated after creation.
    """

    action_id: str
    action_type: str  # "store" | "search" | "recall" | "tool_call" | ...
    payload: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    requires_tools: bool = True  # False = text-only mode acceptable

    def as_text_only(self) -> AgentAction:
        """Return a copy of this action with tools disabled."""
        return AgentAction(
            action_id=self.action_id,
            action_type=self.action_type,
            payload=self.payload,
            context=self.context,
            requires_tools=False,
        )


@dataclass(slots=True)
class AgentResult:
    """The result of an executed agent action.

    Carries the output, degradation level, and optional warnings
    if the result was produced under degraded conditions.
    """

    action_id: str
    success: bool
    output: Any = None
    degradation_level: DegradationLevel = DegradationLevel.L4_GRACEFUL
    warnings: list[str] = field(default_factory=list)
    cortex_fact_id: int | None = None  # If side-effect persisted to CORTEX
    latency_ms: float = 0.0

    def with_warning(self, message: str) -> AgentResult:
        """Return a copy of this result with an additional warning."""
        self.warnings.append(message)
        return self

    @property
    def is_degraded(self) -> bool:
        return bool(self.warnings) or self.degradation_level < DegradationLevel.L4_GRACEFUL


@dataclass(frozen=True, slots=True)
class DegradationReport:
    """Structured report emitted when degradation occurs.

    Designed to be stored in CORTEX as type='error' for future prevention.
    """

    level: DegradationLevel
    component: str
    message: str
    recovery_steps: list[str]
    suggested_alt: str | None
    context: dict[str, Any]
    timestamp: float

    def to_cortex_content(self) -> str:
        """Serialize for CORTEX storage."""
        steps = "; ".join(self.recovery_steps) if self.recovery_steps else "None"
        return (
            f"[{self.level.symbol} L{self.level.value}] {self.component}: {self.message}. "
            f"Recovery: {steps}. Alt: {self.suggested_alt or 'None'}."
        )


# ─── sovereign_execute Decorator ─────────────────────────────────────────────
# Extracted to degradation_executor.py to satisfy the Landauer LOC barrier.
# Re-exported here for backward compatibility.
from cortex.agent.degradation_executor import (  # noqa: E402
    _persist_to_cortex,
    _upgrade_to_l3,
    sovereign_execute,
)

__all__ = [
    # Exception hierarchy
    "SovereignAgentError",
    "SchemaIncompatibilityError",
    "ToolRegistrationError",
    "ModelUnavailableError",
    "AgentDegradedError",
    "AgentCalcificationError",
    # Data contracts
    "DegradationLevel",
    "AgentAction",
    "AgentResult",
    "DegradationReport",
    # Decorator (re-exported from degradation_executor)
    "sovereign_execute",
    "_upgrade_to_l3",
    "_persist_to_cortex",
]
