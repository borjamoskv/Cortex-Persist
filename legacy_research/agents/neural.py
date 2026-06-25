# [C5-REAL] Exergy-Maximized
"""
Neural-Bandwidth Sync (Zero-Latency Intent Ingestion).

Re-exports the neural agent implementation from legacy_research.extensions.agents.neural
to eliminate duplication.
"""

from __future__ import annotations

from legacy_research.extensions.agents.neural import (
    BaseClipboardSensor,
    BaseWindowSensor,
    LinuxClipboardSensor,
    LinuxWindowSensor,
    MacOSClipboardSensor,
    MacOSWindowSensor,
    NeuralContext,
    NeuralHypothesis,
    NeuralIntentEngine,
    WindowsClipboardSensor,
    WindowsWindowSensor,
    calculate_entropy,
    get_clipboard_sensor,
    get_window_sensor,
)

__all__ = [
    "BaseClipboardSensor",
    "BaseWindowSensor",
    "LinuxClipboardSensor",
    "LinuxWindowSensor",
    "MacOSClipboardSensor",
    "MacOSWindowSensor",
    "NeuralContext",
    "NeuralHypothesis",
    "NeuralIntentEngine",
    "WindowsClipboardSensor",
    "WindowsWindowSensor",
    "calculate_entropy",
    "get_clipboard_sensor",
    "get_window_sensor",
]
