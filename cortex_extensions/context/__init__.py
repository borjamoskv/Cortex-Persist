# [C5-REAL] Exergy-Maximized
"""
Context Engine.

Ambient signal collection, multi-signal inference for contextual intelligence,
and HiAgent subgoal compression for long-horizon loops.
"""

from cortex_extensions.context.collector import ContextCollector
from cortex_extensions.context.hiagent import HiAgentTraceManager
from cortex_extensions.context.inference import ContextInference

__all__ = ["ContextCollector", "ContextInference", "HiAgentTraceManager"]
