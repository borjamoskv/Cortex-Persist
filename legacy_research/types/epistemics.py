# [C5-REAL] Exergy-Maximized
"""
Epistemic Types.
Formalizes the taxonomy of knowledge nodes to prevent epistemological mixing.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EpistemicType = Literal[
    "observation", "inference", "simulation", "counterfactual", "consensus", "belief", "hypothesis"
]
CertaintyScore = Literal["C1", "C2", "C3", "C4", "C5"]


class EpistemicNode(BaseModel):
    """Base class for all knowledge represented in the Sovereign State."""
    type: EpistemicType
    certainty: CertaintyScore
    content: str = Field(..., description="The semantic content of this epistemic node.")


class ObservationNode(EpistemicNode):
    """Directly measured or extracted reality."""
    type: Literal["observation"] = "observation"
    certainty: Literal["C4", "C5"] = Field("C5", description="Observations are highly certain.")
    sensor_id: str | None = Field(None, description="The sensor or tool that acquired the observation.")


class InferenceNode(EpistemicNode):
    """Derived logically from other nodes."""
    type: Literal["inference"] = "inference"
    certainty: Literal["C2", "C3", "C4"] = Field("C3", description="Inferences have moderate certainty.")
    source_node_ids: list[str] = Field(
        ..., min_length=1, description="Causal predecessors forming the inference lineage."
    )


class HypothesisNode(EpistemicNode):
    """Future projections or theories that lack empirical confirmation."""
    type: Literal["hypothesis"] = "hypothesis"
    certainty: Literal["C2", "C3"] = Field("C2", description="Hypotheses are untested theoretical claims.")
    test_conditions: list[str] = Field(default_factory=list, description="Conditions needed to elevate to Observation.")



class SimulationNode(EpistemicNode):
    """A scenario or hypothetical branch."""
    type: Literal["simulation"] = "simulation"
    certainty: Literal["C2"] = Field("C2", description="Simulations are low certainty until verified.")
    branch_id: str = Field(..., description="The simulation branch or context ID.")


class CounterfactualNode(EpistemicNode):
    """Alternative or adversarial path."""
    type: Literal["counterfactual"] = "counterfactual"
    certainty: Literal["C1"] = Field("C1", description="Counterfactuals hold the lowest epistemic certainty.")
    divergence_node_id: str = Field(..., description="The reality node from which this diverges.")


class ConsensusNode(EpistemicNode):
    """WBFT quorum reached."""
    type: Literal["consensus"] = "consensus"
    certainty: Literal["C4", "C5"] = Field("C5", description="Consensus approaches absolute certainty.")
    quorum_score: float = Field(..., ge=0.0, le=1.0, description="The cryptographic consensus weight.")
    voter_ids: list[str] = Field(..., min_length=3, description="Minimum 3 nodes required for WBFT.")


class BeliefNode(EpistemicNode):
    """Internal agent belief."""
    type: Literal["belief"] = "belief"
    certainty: Literal["C2", "C3", "C4"] = Field("C3", description="Subjective belief certainty.")
    agent_id: str = Field(..., description="The agent holding this belief.")
