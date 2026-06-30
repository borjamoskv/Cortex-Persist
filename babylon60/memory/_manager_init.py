# [C5-REAL] Exergy-Maximized

import logging
from typing import Any

logger = logging.getLogger("babylon60.memory._manager_init")


def init_dynamic_space(l2: Any, manager: Any) -> Any | None:
    if not l2:
        return None
    try:
        from babylon60.memory.semantic_ram import DynamicSemanticSpace

        return DynamicSemanticSpace(l2, manager=manager)
    except ImportError:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Dynamic semantic space unavailable: %s", exc)
        return None


def init_hologram(l2: Any) -> Any | None:
    if not l2:
        return None
    try:
        from babylon60.memory.hologram import HolographicMemory

        return HolographicMemory(l2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Holographic memory unavailable: %s", exc)
        return None


def init_metamemory() -> Any | None:
    try:
        from babylon60.memory.metamemory import MetamemoryMonitor

        return MetamemoryMonitor()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Metamemory monitor unavailable: %s", exc)
        return None


def init_resonance_gate(l2: Any, endocrine: Any) -> Any | None:
    if not l2:
        return None

    sensor = None
    try:
        from babylon60.extensions.songlines.sensor import TopographicSensor

        sensor = TopographicSensor()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Topographic sensor unavailable for resonance gate: %s", exc)

    try:
        from babylon60.memory.resonance import AdaptiveResonanceGate

        return AdaptiveResonanceGate(
            vector_store=l2,
            songline_sensor=sensor,
            endocrine=endocrine,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Resonance gate unavailable during startup: %s", exc)
        return None
