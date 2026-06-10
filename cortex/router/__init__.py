# [C5-REAL] Exergy-Maximized
"""CORTEX Router - Deterministic Agent Routing.

Routes pipeline requests to the correct agent(s) based on
intent classification and capability matching.
"""

from cortex.router.adapter import ExergyConfigAdapter
from cortex.router.arbitrator import EpistemicArbitrator, ExecutionContext, ModelType
from cortex.router.causal import CausalPolicyGradientRouter, CausalTrajectory
from cortex.router.contract import (
    CognitiveMode,
    InformationState,
    RoutingContext,
    RoutingDecision,
    Severity,
)
from cortex.router.nash import NashCausalRouter, RoutingUtilities
from cortex.router.policy import EpistemicPolicyNetwork, SignalVector
from cortex.router.router import AgentRouter

__all__ = [
    "AgentRouter",
    "CognitiveMode",
    "EpistemicArbitrator",
    "ExergyConfigAdapter",
    "ExecutionContext",
    "InformationState",
    "ModelType",
    "EpistemicPolicyNetwork",
    "RoutingContext",
    "RoutingDecision",
    "Severity",
    "SignalVector",
    "CausalPolicyGradientRouter",
    "CausalTrajectory",
    "NashCausalRouter",
    "RoutingUtilities",
]
