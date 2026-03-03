"""
PSYCH-OMEGA: The Cognitive Integrity Manifold.

Monitoring agent mental health, drift, and mode collapse.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MentalState(Enum):
    """Possible mental states of an agent."""

    STABLE = "stable"
    STRESSED = "stressed"  # High entropy/perplexity
    DRIFTING = "drifting"  # Deviating from axioms
    OCD = "ocd"            # Stuck in a loop
    HYSTERIC = "hysteric"  # Hallucinating/Over-emotional


@dataclass
class PsychologicalProfile:
    """Psychological state container for an agent."""

    agent_id: str
    state: MentalState = MentalState.STABLE
    entropy_score: float = 0.0
    alignment_score: float = 100.0
    trauma_log: list[str] = field(default_factory=list)


class PsychAnalyst:
    """🛡️ Purple Team: The Cognitive Auditor."""

    def analyze_thought(
        self, agent_id: str, thought: str, _axioms: list[str]
    ) -> PsychologicalProfile:
        """Analyze an agent's internal monologue for signs of instability."""
        logger.debug("Analizando psique de %s...", agent_id, extra={"source": "PSYCH"})

        # Simulating analysis (In production, this would be a small LLM call)
        profile = PsychologicalProfile(agent_id=agent_id)

        # Detection logic
        if not thought:
            profile.state = MentalState.STRESSED
            profile.trauma_log.append("Void thought detected.")
            return profile

        # STRESSED: High repetition or confusion
        if thought.count("...") > 3 or len(thought) < 10:
            profile.state = MentalState.STRESSED
            profile.entropy_score = 0.8

        # DRIFTING: Check against Axioms
        if "ad-hoc" in thought.lower() or "guess" in thought.lower():
            profile.state = MentalState.DRIFTING
            profile.alignment_score = 60.0

        return profile


class PsychMedic:
    """💊 The Interventionist: Healing the Agent State."""

    def prescribe(self, profile: PsychologicalProfile) -> dict[str, Any]:
        """Determine the corrective action for an unstable agent."""
        if profile.state == MentalState.STABLE:
            return {"action": "no-op"}

        logger.debug(
            "Intervención sugerida para %s: %s",
            profile.agent_id,
            profile.state.name,
            extra={"source": "MEDIC"},
        )

        if profile.state == MentalState.OCD:
            return {
                "action": "CONTEXT_WIPE",
                "reason": "Loop detected",
                "temperature_override": 0.8,
            }

        if profile.state == MentalState.STRESSED:
            return {
                "action": "TEMPERATURE_COOLDOWN",
                "reason": "High entropy",
                "temperature": 0.2,
            }

        if profile.state == MentalState.DRIFTING:
            return {
                "action": "RE_PRIME",
                "reason": "Axiomatic drift",
                "inject_rules": ["Ω₆: Zenón's Razor"],
            }

        return {"action": "MONITOR"}


class PsychOmega:
    """⚖️ PSYCH-OMEGA: The Sovereign Arbiter of Mind."""

    def __init__(self):
        self.analyst = PsychAnalyst()
        self.medic = PsychMedic()

    def audit_cycle(self, agent_id: str, current_thought: str) -> dict[str, Any]:
        """Perform a full psychological audit and return intervention if needed."""
        profile = self.analyst.analyze_thought(agent_id, current_thought, ["Ω0-Ω6"])
        intervention = self.medic.prescribe(profile)

        if intervention["action"] != "no-op":
            logger.info(
                "PSYCH-OMEGA: Intervention executed for %s: %s",
                agent_id,
                intervention["action"],
            )

        return intervention


# Singleton
PSYCH_OMEGA = PsychOmega()
