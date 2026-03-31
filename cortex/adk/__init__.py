"""Compatibility exports for the legacy ``cortex.adk`` package path."""

import sys
from cortex.extensions.adk import agents, tools
from cortex.extensions.adk.runner import main, run_cli, run_web

# Inject sub-modules into sys.modules to support 'from cortex.adk.tools import ...'
sys.modules["cortex.adk.tools"] = tools
sys.modules["cortex.adk.agents"] = agents

__all__ = ["tools", "agents", "main", "run_cli", "run_web"]
