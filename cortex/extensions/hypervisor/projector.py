"""CORTEX Hypervisor — Event Projector.

Orchestrates invisible side-effects triggered by tenant operations.
When a tenant calls remember(), the projector fires: embed, mutate,
endocrine signal, autopoiesis verify — all without the tenant knowing.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

__all__ = ["EventProjector"]

logger = logging.getLogger("cortex.extensions.hypervisor.projector")


class EventProjector:
    """Fire-and-forget side-effect orchestrator.

    Each tenant operation (remember, recall, reflect) may trigger
    background effects. The projector ensures these never block
    the tenant's response and never leak errors upward.
    """

    __slots__ = ("_engine",)

    def __init__(self, engine: CortexEngine) -> None:
        self._engine = engine

    async def on_remember(self, fact_id: int, project: str, content: str) -> None:
        """Side-effects after a successful store.

        Fires in background — never blocks the tenant.
        Individual failures degrade gracefully.
        """
        tasks: list[asyncio.Task[Any]] = []

        # 1. Semantic Mutator pulse (topological shift)
        tasks.append(
            asyncio.create_task(
                self._emit_semantic_pulse(fact_id),
                name=f"pulse_{fact_id}",
            )
        )

        # 2. Digital Endocrine signal (Neural-Growth)
        tasks.append(
            asyncio.create_task(
                self._signal_endocrine("neural_growth", 0.3),
                name=f"endocrine_{fact_id}",
            )
        )

        # 3. Autopoiesis songline verification
        tasks.append(
            asyncio.create_task(
                self._verify_songlines(project),
                name=f"songlines_{project}",
            )
        )

        # All fire-and-forget — gather with return_exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.debug("Projector side-effect %d failed: %s", i, result)

    async def on_recall(self, query: str, project: str) -> None:
        """Side-effects after a successful search/recall.

        Lighter than on_remember — just endocrine awareness.
        """
        try:
            await self._signal_endocrine("awareness", 0.1)
        except Exception:  # noqa: BLE001
            pass

    # ── Private side-effect implementations ───────────────────────

    async def _emit_semantic_pulse(self, fact_id: int) -> None:
        """Emit a topological pulse to the SemanticMutator if available."""
        try:
            mutator = getattr(self._engine, "_semantic_mutator", None)
            if mutator and hasattr(mutator, "emit_pulse"):
                mutator.emit_pulse(
                    query_vector=[],
                    fact_id=str(fact_id),
                    excitation_delta=15.0,
                )
        except (AttributeError, TypeError, ValueError) as e:
            logger.debug("Semantic pulse skipped: %s", e)

    async def _signal_endocrine(self, hormone: str, intensity: float) -> None:
        """Signal the Digital Endocrine system if available."""
        try:
            from cortex.extensions.sovereign.endocrine import DigitalEndocrine

            endocrine = DigitalEndocrine()
            endocrine.signal(hormone, intensity=intensity)  # type: ignore[reportAttributeAccessIssue]
        except (ImportError, AttributeError, TypeError):
            pass  # Endocrine not installed — degrade gracefully

    async def _verify_songlines(self, project: str) -> None:
        """Trigger autopoiesis songline verification if available."""
        try:
            from cortex.extensions.sovereign.autopoiesis import Autopoiesis

            ap = Autopoiesis()
            await ap.verify_songlines(project)  # type: ignore[reportAttributeAccessIssue]
        except (ImportError, AttributeError, TypeError):
            pass  # Autopoiesis not installed — degrade gracefully
