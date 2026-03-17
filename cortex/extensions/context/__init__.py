"""
CORTEX v5.0 — Context Engine.

Ambient signal collection, multi-signal inference for contextual intelligence,
and HiAgent subgoal compression for long-horizon loops.
"""

from cortex.extensions.context.collector import ContextCollector
from cortex.extensions.context.hiagent import HiAgentTraceManager
from cortex.extensions.context.inference import ContextInference

__all__ = ["ContextCollector", "ContextInference", "HiAgentTraceManager"]
