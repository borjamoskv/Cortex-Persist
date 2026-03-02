"""CORTEX v6+ — Agent package."""

from cortex.agent.degradation import (
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
    sovereign_execute,
)
from cortex.agent.schema import AgentRole, GuardrailConfig, MemoryConfig

__all__ = [
    # schema
    "AgentRole",
    "GuardrailConfig",
    "MemoryConfig",
    # degradation
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
    "sovereign_execute",
]
