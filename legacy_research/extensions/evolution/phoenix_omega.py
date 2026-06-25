# [C5-REAL] Exergy-Maximized
"""
PHOENIX-OMEGA: Motor de Transformación Atómica y Escalado Estructural
Wrapper para el core engine en cortex.engine.phoenix_omega.
"""

from legacy_research.engine.phoenix_omega import (
    AtomicPhase,
    BaseEngine,
    PhaseStatus,
    PhoenixOrchestrator,
    PhoenixState,
    StructuralAtom,
)

__all__ = [
    "AtomicPhase",
    "BaseEngine",
    "PhaseStatus",
    "PhoenixOrchestrator",
    "PhoenixState",
    "StructuralAtom",
]

if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    # Test boot sequence via proxy
    orchestrator = PhoenixOrchestrator()
    asyncio.run(orchestrator.ignite([Path(__file__)]))
