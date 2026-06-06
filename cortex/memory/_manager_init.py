# [C5-REAL] Exergy-Maximized

import logging
from typing import Any

logger = logging.getLogger("cortex.memory._manager_init")


def init_dynamic_space(l2: Any, manager: Any) -> Any | None:
    if not l2:
        return None
    try:
        from cortex.memory.semantic_ram import DynamicSemanticSpace

        return DynamicSemanticSpace(l2, manager=manager)
    except ImportError:
        return None
    except Exception as exc:
        logger.warning("Dynamic semantic space unavailable: %s", exc)
        return None


def init_hologram(l2: Any) -> Any | None:
    if not l2:
        return None
    try:
        from cortex.memory.hologram import HolographicMemory

        return HolographicMemory(l2)
    except Exception as exc:
        logger.warning("Holographic memory unavailable: %s", exc)
        return None


def init_metamemory() -> Any | None:
    try:
        from cortex.memory.metamemory import MetamemoryMonitor

        return MetamemoryMonitor()
    except Exception as exc:
        logger.warning("Metamemory monitor unavailable: %s", exc)
        return None


def init_resonance_gate(l2: Any, endocrine: Any) -> Any | None:
    if not l2:
        return None

    sensor = None
    try:
        from cortex.extensions.songlines.sensor import TopographicSensor

        sensor = TopographicSensor()
    except Exception as exc:
        logger.warning("Topographic sensor unavailable for resonance gate: %s", exc)

    try:
        from cortex.memory.resonance import AdaptiveResonanceGate

        return AdaptiveResonanceGate(
            vector_store=l2,
            songline_sensor=sensor,
            endocrine=endocrine,
        )
    except Exception as exc:
        logger.warning("Resonance gate unavailable during startup: %s", exc)
        return None
