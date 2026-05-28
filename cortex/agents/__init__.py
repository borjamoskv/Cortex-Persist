"""CORTEX Agents — runtime public API.

Exposes the core agent runtime classes. Extension-layer prompts and pitch
templates remain in ``cortex.extensions.agents``.
"""

from __future__ import annotations

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus, SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import (
    AgentMessage,
    MessageKind,
    MessageState,
    new_message,
)
from cortex.agents.schema import AgentRole
from cortex.agents.state import AgentState, AgentStatus, WorkingMemory
from cortex.agents.supervisor import Supervisor
from cortex.agents.tools import Tool, ToolRegistry

__all__ = [
    # Core runtime
    "BaseAgent",
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
