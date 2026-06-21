# [C5-REAL] Exergy-Maximized
from dataclasses import dataclass
from typing import Any

import numpy as np

from cortex.simulation.primitives import MemoryTrajectory, SimulationField
from cortex.simulation.thermodynamics import ThermodynamicState


@dataclass
class NarrativeVector:
    trajectory_id: str
    semantic_tension: float
    temporal_consistency: float
    energy_signature: float
    phase_alignment: float
    particles: list[Any]  # Keep a reference to particles if needed


@dataclass
class ActionOutput:
    type: str  # DIRECT_ACTION, GUIDED_DECISION, NARRATIVE_FIELD
    content: str | list[str] | dict[str, Any]
    confidence: float
    energy_cost: float


class NarrativeCompiler:
    """
    Converts probabilistic trajectories and thermodynamic states into
    executable actions, guided decisions, or narrative fields.
    """

    def __init__(self):
        pass

    def _build_vector_field(self, trajectories: list[MemoryTrajectory]) -> list[NarrativeVector]:
        field_vectors = []
        for i, t in enumerate(trajectories):
            # Semantic tension: variance of intent alignment inside the trajectory
            tension = (
                float(np.var([p.probability_mass for p in t.particles]))
                if len(t.particles) > 1
                else 0.0
            )

            # Temporal consistency: inverse of temporal gap variance
            timestamps = [p.temporal_phase for p in t.particles if p.temporal_phase > 0]
            consistency = 1.0 / (1.0 + np.var(timestamps)) if len(timestamps) > 1 else 1.0

            # Energy signature: approximated from entropy penalty
            energy_sig = t.entropy_penalty * 10.0

            nv = NarrativeVector(
                trajectory_id=f"traj_{i}",
                semantic_tension=tension,
                temporal_consistency=consistency,
                energy_signature=energy_sig,
                phase_alignment=t.coherence_score,
                particles=t.particles,
            )
            field_vectors.append(nv)
        return field_vectors

    def _energy_filter(
        self, field: list[NarrativeVector], budget_threshold: float
    ) -> list[NarrativeVector]:
        # remove trajectories where energy_cost > budget_threshold
        return [nv for nv in field if nv.energy_signature <= budget_threshold]

    def _collapse_direct(self, field: list[NarrativeVector]) -> ActionOutput:
        """
        SOLID phase: single trajectory, low entropy. Factual compression.
        """
        if not field:
            return ActionOutput(
                type="DIRECT_ACTION", content="NO_ACTION", confidence=0.0, energy_cost=0.0
            )

        # Fall into action attractor (argmax coherence & efficiency)
        best_nv = max(field, key=lambda nv: nv.phase_alignment - nv.energy_signature)

        # In reality, this would map the particles to a specific executable command or hard fact
        content = f"EXECUTE_SOLID_COMPRESSION:[{best_nv.trajectory_id}]"

        return ActionOutput(
            type="DIRECT_ACTION",
            content=content,
            confidence=best_nv.phase_alignment,
            energy_cost=best_nv.energy_signature,
        )

    def _guided_decision(self, field: list[NarrativeVector]) -> ActionOutput:
        """
        LIQUID phase: 2-5 weighted options. Ranked but not collapsed.
        """
        if not field:
            return ActionOutput(type="GUIDED_DECISION", content=[], confidence=0.0, energy_cost=0.0)

        # Sort by attractor
        sorted_field = sorted(
            field, key=lambda nv: nv.phase_alignment - nv.energy_signature, reverse=True
        )
        top_options = sorted_field[: min(5, len(sorted_field))]

        content = [
            {"trajectory": nv.trajectory_id, "weight": nv.phase_alignment} for nv in top_options
        ]
        avg_confidence = float(np.mean([nv.phase_alignment for nv in top_options]))
        total_energy = float(np.sum([nv.energy_signature for nv in top_options]))

        return ActionOutput(
            type="GUIDED_DECISION",
            content=content,
            confidence=avg_confidence,
            energy_cost=total_energy,
        )

    def _narrative_cloud(self, field: list[NarrativeVector]) -> ActionOutput:
        """
        PLASMA phase: multiple simultaneous interpretations. Probabilistic narrative.
        """
        if not field:
            return ActionOutput(type="NARRATIVE_FIELD", content={}, confidence=0.0, energy_cost=0.0)

        content = {
            "manifold_size": len(field),
            "tensions": [nv.semantic_tension for nv in field],
            "interpretations": [nv.trajectory_id for nv in field],
        }

        avg_confidence = float(np.mean([nv.phase_alignment for nv in field]))
        total_energy = float(np.sum([nv.energy_signature for nv in field]))

        # Superposition tax is high
        return ActionOutput(
            type="NARRATIVE_FIELD",
            content=content,
            confidence=avg_confidence,
            energy_cost=total_energy * 1.5,
        )

    def compile(
        self, simulation_field: SimulationField, thermo_state: ThermodynamicState
    ) -> ActionOutput:
        nvf = self._build_vector_field(simulation_field.trajectories)
        filtered = self._energy_filter(nvf, thermo_state.energy_budget)

        # Phase Conditioning
        phase = thermo_state.phase

        # Fallback if filtered is empty due to extreme energy costs
        if not filtered:
            return ActionOutput(
                type="DIRECT_ACTION",
                content="ZERO_ENERGY_BUDGET_FALLBACK: Minimal factual kernel.",
                confidence=1.0,
                energy_cost=0.0,
            )

        if phase == "SOLID":
            return self._collapse_direct(filtered)
        elif phase == "LIQUID":
            return self._guided_decision(filtered)
        else:  # PLASMA
            return self._narrative_cloud(filtered)
