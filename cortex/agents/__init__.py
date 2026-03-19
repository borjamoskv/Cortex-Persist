"""CORTEX Agent Runtime Package."""

from __future__ import annotations

from cortex.agents.agent_tools import (
    FileReadTool,
    FileWriteTool,
    GitTool,
    TerminalTool,
    TestRunnerTool,
    register_builtin_tools,
)
from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus, SqliteMessageBus
from cortex.agents.executor import AutonomousExecutor
from cortex.agents.manifest import AgentManifest

# MCP Client Additions
from cortex.agents.mcp_client import McpConnectionManager, McpToolWrapper, register_mcp_tools
from cortex.agents.mcp_config import McpServerConfig, load_mcp_config
from cortex.agents.message_schema import AgentMessage, MessageType, new_message
from cortex.agents.session import (
    AgentSession,
    SessionStatus,
    SessionStep,
    SessionStore,
    StepStatus,
)
from cortex.agents.state import AgentState, AgentStatus, WorkingMemory
from cortex.agents.supervisor import Supervisor
from cortex.agents.tools import Tool, ToolRegistry

__all__ = [
    "AgentManifest",
    "AgentMessage",
    "AgentSession",
    "SessionStep",
    "StepStatus",
    "AgentState",
    "AgentStatus",
    "AutonomousExecutor",
    "BaseAgent",
    "FileReadTool",
    "FileWriteTool",
    "GitTool",
    "MessageBus",
    "MessageType",
    "SessionStatus",
    "SessionStore",
    "SqliteMessageBus",
    "Supervisor",
    "TerminalTool",
    "TestRunnerTool",
    "Tool",
    "ToolRegistry",
    "WorkingMemory",
    "new_message",
    "register_builtin_tools",
    # MCP Client
    "McpConnectionManager",
    "McpServerConfig",
    "McpToolWrapper",
    "load_mcp_config",
    "register_mcp_tools",
]
