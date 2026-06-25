# [C5-REAL] Exergy-Maximized
"""CORTEX Router - Deterministic Agent Routing.

Routes pipeline requests to the correct agent(s) based on
intent classification and capability matching.
"""

from legacy_research.router.adapter import ExergyConfigAdapter
from legacy_research.router.arbitrator import ExecutionContext, ModelType, RetrievalArbitrator
from legacy_research.router.causal import CausalPolicyGradientRouter, CausalTrajectory
from legacy_research.router.contract import (
    CognitiveMode,
    InformationState,
    RoutingContext,
    RoutingDecision,
    Severity,
)
from legacy_research.router.nash import NashCausalRouter, RoutingUtilities
from legacy_research.router.policy import RetrievalPolicyNetwork, SignalVector
from legacy_research.router.router import AgentRouter

__all__ = [
    "AgentRouter",
    "CognitiveMode",
    "RetrievalArbitrator",
    "ExergyConfigAdapter",
    "ExecutionContext",
    "InformationState",
    "ModelType",
    "RetrievalPolicyNetwork",
    "RoutingContext",
    "RoutingDecision",
    "Severity",
    "SignalVector",
    "CausalPolicyGradientRouter",
    "CausalTrajectory",
    "NashCausalRouter",
    "RoutingUtilities",
]
