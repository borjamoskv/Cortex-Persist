"""
CORTEX v5.0 — Context Engine.

Ambient signal collection, multi-signal inference for contextual intelligence,
and HiAgent subgoal compression for long-horizon loops.
"""

from cortex.context.collector import ContextCollector
from cortex.context.hiagent import HiAgentTraceManager
from cortex.context.inference import ContextInference

__all__ = ["ContextCollector", "ContextInference", "HiAgentTraceManager"]
