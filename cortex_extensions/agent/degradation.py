# [C5-REAL] Exergy-Maximized
"""Sovereign Degradation Protocol (Ω₅ Applied).

Materializes §14 of AGENTICA.md: "Degradación Soberana - Ω₅ Aplicado a Sistemas Agénticos".

Philosophy:
  Robustness is not measured by the absence of failures, but by the
  informational quality of the failure when it occurs.

  L0 - Hard Crash  : Silent termination. Pure entropy.
  L1 - Opaque Error: Generic message. No recovery path.
  L2 - Informed    : Cause identified. No action suggested.
  L3 - Actionable  : Cause + recovery path + alternatives.  ← Sovereign minimum
  L4 - Graceful    : Operates at reduced capacity, notifies limits. ← Antifragile

CORTEX targets L3–L4. An agent that fails silently is not broken - it is incomplete.

Axiom derivation: Ω₅ (Antifragile by Default) - Error = gradient.
A failure that produces no information produces no gradient.
Without gradient, no learning. Without learning, the system calcifies.

Usage::

    from cortex_extensions.agent.degradation import (
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

from .degradation_executor import (
    _persist_to_cortex,
    _upgrade_to_l3,
    sovereign_execute,
)
from .degradation_types import (
    AgentAction,
    AgentCalcificationError,
    AgentDegradedError,
    AgentResult,
    DegradationLevel,
    DegradationReport,
    ModelUnavailableError,
    SchemaIncompatibilityError,
    SovereignAgentError,
    ToolRegistrationError,
)

__all__ = [
    "AgentAction",
    "AgentCalcificationError",
    "AgentDegradedError",
    "AgentResult",
    "DegradationLevel",
    "DegradationReport",
    "ModelUnavailableError",
    "SchemaIncompatibilityError",
    "SovereignAgentError",
    "ToolRegistrationError",
    "_persist_to_cortex",
    "_upgrade_to_l3",
    "sovereign_execute",
]
