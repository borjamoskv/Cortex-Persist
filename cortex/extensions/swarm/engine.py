# [C5-REAL] Exergy-Maximized
"""
Sovereign Swarm Execution Pipeline (Agent Routing Topology)

This pipeline enforces the STRICT execution hierarchy for OMEGA/APEX skills,
preventing AST ghosts and thermodynamic debt caused by concurrent mutations.

Pipeline:
  1. SORTU_APEX: Ingress Meta-Dispatcher.
  2. SINGULARITY_NEXUS: State & Ghost Synchronization (Read-Only).
  3. EXERGY_SINGULARITY: Constraint Mapping (Read-Only).
  4. AUTOCOGNITION_OMEGA: Epistemic Verifier (Read-Only).
  5. LEA_OMEGA: Surgical Executer / Sole Mutator (Write).
"""

import logging
from enum import Enum

logger = logging.getLogger("cortex.extensions.swarm.engine")


class SwarmSkillPhase(Enum):
    INGRESS = "Sortu-APEX"
    SYNC = "Singularity-Nexus"
    CONSTRAINT = "Exergy-Singularity-OMEGA"
    VERIFICATION = "Autocognition-OMEGA"
    MUTATION = "LEA-OMEGA"


class SovereignPipeline:
    """Enforces the strict execution hierarchy for CORTEX OMEGA skills."""

    def __init__(self):
        self._current_phase: SwarmSkillPhase | None = None

        # Define role restrictions
        self.ROLE_RESTRICTIONS = {
            SwarmSkillPhase.INGRESS: {"can_mutate": False, "role": "Meta-Dispatcher"},
            SwarmSkillPhase.SYNC: {"can_mutate": False, "role": "State Synchronizer"},
            SwarmSkillPhase.CONSTRAINT: {"can_mutate": False, "role": "Constraint Mapper"},
            SwarmSkillPhase.VERIFICATION: {"can_mutate": False, "role": "Epistemic Verifier"},
            SwarmSkillPhase.MUTATION: {"can_mutate": True, "role": "Surgical Mutator"},
        }

    def advance_to(self, phase: SwarmSkillPhase) -> None:
        """Advance the pipeline to the specified phase."""
        self._current_phase = phase
        logger.info(
            "🛡️ [SWARM-ROUTING] Pipeline advanced to %s (Role: %s, Mutator: %s)",
            phase.value,
            self.ROLE_RESTRICTIONS[phase]["role"],
            self.ROLE_RESTRICTIONS[phase]["can_mutate"],
        )

    def can_mutate(self, skill_name: str) -> bool:
        """
        AX-047 Gate: Only LEA-OMEGA can mutate the state during this pipeline.
        All other skills must be strictly Read-Only.
        """
        # Ensure only the active phase matches the requested skill
        if self._current_phase and self._current_phase.value != skill_name:
            logger.warning(
                "🛡️ [SWARM-ROUTING] Skill %s attempted action during %s phase. Denied.",
                skill_name,
                self._current_phase.value,
            )
            return False

        try:
            phase_enum = SwarmSkillPhase(skill_name)
            return self.ROLE_RESTRICTIONS[phase_enum]["can_mutate"]
        except ValueError:
            logger.error(
                "🛡️ [SWARM-ROUTING] Unknown skill %s attempted mutation. Denied.", skill_name
            )
            return False


def get_sovereign_pipeline() -> SovereignPipeline:
    """Singleton instance of the Sovereign Pipeline."""
    if not hasattr(get_sovereign_pipeline, "_instance"):
        get_sovereign_pipeline._instance = SovereignPipeline()  # type: ignore
    return get_sovereign_pipeline._instance  # type: ignore
