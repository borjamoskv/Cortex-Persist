# [C5-REAL] Exergy-Maximized
"""CORTEX Agents - runtime public API.

Exposes the core agent runtime classes. Extension-layer prompts and pitch
templates remain in ``cortex.extensions.agents``.
"""

from __future__ import annotations

from legacy_research.agents.base import BaseAgent, ReactiveTaskAgent
from legacy_research.agents.bus import MessageBus, SqliteMessageBus
from legacy_research.agents.consolidator import ConsolidatorAgent
from legacy_research.agents.manifest import AgentManifest
from legacy_research.agents.message_schema import (
    AgentMessage,
    MessageKind,
    MessageState,
    new_message,
)
from legacy_research.agents.ontological_consolidator import OntologicalConsolidator
from legacy_research.agents.schema import AgentRole
from legacy_research.agents.state import AgentState, AgentStatus, WorkingMemory
from legacy_research.agents.supervisor import Supervisor
from legacy_research.agents.tools import Tool, ToolRegistry

__all__ = [
    # Core runtime
    "BaseAgent",
    "ReactiveTaskAgent",
    "ConsolidatorAgent",
    "OntologicalConsolidator",
    "Supervisor",
    # Manifest & schema
    "AgentManifest",
    "AgentRole",
    # State
    "AgentState",
    "AgentStatus",
    "WorkingMemory",
    # Messaging
    "AgentMessage",
    "MessageBus",
    "MessageKind",
    "MessageState",
    "SqliteMessageBus",
    "new_message",
    # Tools
    "Tool",
    "ToolRegistry",
]
