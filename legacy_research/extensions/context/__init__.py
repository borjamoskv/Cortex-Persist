# [C5-REAL] Exergy-Maximized
"""
Context Engine.

Ambient signal collection, multi-signal inference for contextual intelligence,
and HiAgent subgoal compression for long-horizon loops.
"""

from legacy_research.extensions.context.collector import ContextCollector
from legacy_research.extensions.context.hiagent import HiAgentTraceManager
from legacy_research.extensions.context.inference import ContextInference

__all__ = ["ContextCollector", "ContextInference", "HiAgentTraceManager"]
