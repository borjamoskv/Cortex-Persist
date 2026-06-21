# [C5-REAL] Exergy-Maximized
"""Router Contract v1 — Single Source of Truth for Cognitive Routing.

Defines the formal input/output schemas, precedence rules, fallback hierarchy,
and determinism guarantees that ANY routing decision must respect.

This is a pure data contract. It does NOT execute routing.
It does NOT import runtime modules.
It does NOT read YAML files.

Any component that makes routing decisions (AgentRouter, RetrievalArbitrator,
RetrievalPolicyNetwork, ExergyConfigAdapter) MUST produce outputs that
conform to RoutingDecision and respect the precedence defined here.

Architecture Invariant:
    contract.py is NEVER modified by runtime.
    contract.py is NEVER dependent on config files.
    contract.py is the arbiter when policy and runtime disagree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

# ─── Cognitive Modes ──────────────────────────────────────────────────────


@unique
class CognitiveMode(str, Enum):
    """The four cognitive execution modes.

    These map 1:1 to the routing_rules in cognitive_routing_matrix.yaml,
    but the contract defines them independently — YAML is a policy spec,
    this is the execution schema.
    """

    NORMAL = "normal"
    """Routine maintenance, isolated bugs, config changes."""

    DEEP_THINK = "deep_think"
    """Irreversible decisions or compound effects requiring explicit CoT."""

    DEEP_RESEARCH = "deep_research"
    """Information deficit: required knowledge is missing, stale, or unreliable."""

    ULTRA_THINK = "ultra_think"
    """Catastrophic risk: critical severity or blast_radius >= 3."""


# ─── Severity ─────────────────────────────────────────────────────────────


@unique
class Severity(str, Enum):
    """Impact magnitude independent of scope."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ─── Information State ────────────────────────────────────────────────────


@dataclass(frozen=True)
class InformationState:
    """Three independent axes for information quality assessment.

    Each axis is evaluated independently. A deficit on ANY single axis
    is sufficient to trigger DEEP_RESEARCH mode.
    """

    exists_internally: bool = True
    """Does the required information exist within workspace/memory?"""

    is_reliable: bool = True
    """Is the information from a verified C5-REAL source?"""

    is_current: bool = True
    """Has the information been validated within its TTL?"""

    @property
    def has_deficit(self) -> bool:
        """True if ANY axis indicates an information deficit."""
        return not (self.exists_internally and self.is_reliable and self.is_current)


# ─── Routing Context (Input Schema) ──────────────────────────────────────


@dataclass(frozen=True)
class RoutingContext:
    """Complete input for a routing decision.

    This is the ONLY valid input type for routing resolution.
    Any routing component that accepts different inputs must
    internally map them to this schema.
    """

    severity: Severity = Severity.LOW
    """Impact magnitude of the change."""

    blast_radius: int = 0
    """Number of modules affected by the change (0 = self-contained)."""

    info_state: InformationState = field(default_factory=InformationState)
    """Quality assessment of available information."""

    intent_text: str = ""
    """Raw intent text for pattern-based routing (optional, for AgentRouter compat)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Opaque metadata bag for downstream consumers. Contract ignores this."""


# ─── Routing Decision (Output Schema) ────────────────────────────────────


@dataclass(frozen=True)
class RoutingDecision:
    """The output of any routing resolution.

    Every routing component MUST produce this exact structure.
    No additional fields. No optional overrides. No escape hatches.
    """

    mode: CognitiveMode
    """The resolved cognitive execution mode."""

    gate_id: str
    """Which precedence gate triggered this decision (e.g., 'GATE_ULTRA')."""

    rationale: str
    """Human-readable justification for the routing decision."""

    confidence: float = 1.0
    """Confidence in the decision [0.0, 1.0]. Deterministic gates always emit 1.0."""

    source: str = "contract"
    """Which component produced this decision (for audit trail)."""


# ─── Precedence Rules (Deterministic, Short-Circuit OR) ──────────────────


# Gate evaluation order is STRICT. First match wins. No backtracking.
# This is the canonical precedence — if YAML or runtime disagree, this wins.

PRECEDENCE_GATES: list[dict[str, Any]] = [
    {
        "id": "GATE_ULTRA",
        "order": 1,
        "description": "Catastrophe / UltraThink (short-circuit)",
        "condition": "severity == CRITICAL OR blast_radius >= 3",
        "result": CognitiveMode.ULTRA_THINK,
        "deterministic": True,
    },
    {
        "id": "GATE_RESEARCH",
        "order": 2,
        "description": "Information Deficit / Deep Research",
        "condition": "info_state.has_deficit == True",
        "result": CognitiveMode.DEEP_RESEARCH,
        "deterministic": True,
    },
    {
        "id": "GATE_DEEP",
        "order": 3,
        "description": "Structural Decisions / Deep Think",
        "condition": "blast_radius == 2 OR severity == HIGH",
        "result": CognitiveMode.DEEP_THINK,
        "deterministic": True,
    },
    {
        "id": "GATE_NORMAL",
        "order": 4,
        "description": "Default / Normal",
        "condition": "default",
        "result": CognitiveMode.NORMAL,
        "deterministic": True,
    },
]


# ─── Determinism Guarantees ──────────────────────────────────────────────


CONTRACT_VERSION = "1.0.0"

GUARANTEES = {
    "deterministic": True,
    "idempotent": True,
    "side_effect_free": True,
    "total_function": True,  # Every valid RoutingContext produces a RoutingDecision
    "precedence_fixed": True,  # Gate order is immutable at runtime
    "single_source_of_truth": "contract.py (this file)",
}


# ─── Contract Resolver (Reference Implementation) ───────────────────────


def resolve(ctx: RoutingContext) -> RoutingDecision:
    """Canonical routing resolution. Pure function. No side effects.

    This is the REFERENCE implementation. Any adapter, arbitrator, or
    policy network must produce results equivalent to this function
    for the same input, or explicitly document and justify deviations.
    """
    # GATE 1: Catastrophe (short-circuit on severity OR blast_radius)
    if ctx.severity == Severity.CRITICAL or ctx.blast_radius >= 3:
        return RoutingDecision(
            mode=CognitiveMode.ULTRA_THINK,
            gate_id="GATE_ULTRA",
            rationale=(
                f"severity={ctx.severity.value}, blast_radius={ctx.blast_radius}. "
                "Critical severity short-circuits blast_radius check."
            ),
            source="contract.resolve",
        )

    # GATE 2: Information Deficit
    if ctx.info_state.has_deficit:
        deficits = []
        if not ctx.info_state.exists_internally:
            deficits.append("missing")
        if not ctx.info_state.is_reliable:
            deficits.append("unreliable")
        if not ctx.info_state.is_current:
            deficits.append("stale")
        return RoutingDecision(
            mode=CognitiveMode.DEEP_RESEARCH,
            gate_id="GATE_RESEARCH",
            rationale=f"Information deficit: {', '.join(deficits)}.",
            source="contract.resolve",
        )

    # GATE 3: Structural / High severity
    if ctx.blast_radius == 2 or ctx.severity == Severity.HIGH:
        return RoutingDecision(
            mode=CognitiveMode.DEEP_THINK,
            gate_id="GATE_DEEP",
            rationale=(
                f"severity={ctx.severity.value}, blast_radius={ctx.blast_radius}. "
                "Irreversible decisions require explicit chain-of-thought."
            ),
            source="contract.resolve",
        )

    # GATE 4: Default
    return RoutingDecision(
        mode=CognitiveMode.NORMAL,
        gate_id="GATE_NORMAL",
        rationale="Routine operation. No escalation triggers matched.",
        source="contract.resolve",
    )
