"""
CORTEX v5.0 — Real-Time Perception Engine.

Three-layer behavioral perception:
  1. FileActivityObserver — watches workspace via watchdog FSEvents
  2. BehavioralInference — infers intent from activity patterns
  3. PerceptionRecorder — auto-records episodes when confidence is high

Re-exports all public symbols for backward-compatible imports.
"""

from cortex.perception.inference import compute_event_stats, infer_behavior
from cortex.perception.observer import FileActivityObserver
from cortex.perception.pipeline import PerceptionPipeline, PerceptionRecorder
from cortex.perception.base import (
    BehavioralSnapshot,
    FileEvent,
    classify_file,
    infer_project_from_path,
    should_ignore,
)

__all__ = [
    "BehavioralSnapshot",
    "FileActivityObserver",
    "FileEvent",
    "PerceptionPipeline",
    "PerceptionRecorder",
    "classify_file",
    "compute_event_stats",
    "infer_behavior",
    "infer_project_from_path",
    "should_ignore",
]
