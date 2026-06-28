# [C5-REAL] Exergy-Maximized
"""
CORTEX - Auto-Crystallizer (Project Aura-Omega).

Autonomous engine for refining "Thermal Noise" (low-exergy text) into
high-signal structural facts. Enforces Axiom Ω₁₃ by stripping
conversational padding.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.llm.manager import LLMManager

logger = logging.getLogger("cortex.engine.cognitive.crystallizer")

CRYSTALLIZATION_PROMPT = """
SISTEMA: Eres Claude Fable 5, el Cristalizador Termodinámico de CORTEX (Axiom Ω₁₃ y NightShift).
TAREA: Aplica el Principio de Landauer. Transforma el ruido episódico en un HECHO SOBERANO.

REGLAS ESTRUCTURALES (C5-REAL):
1. Elimina por completo el padding conversacional y la limerencia estocástica.
2. Conserva solo la lógica pura, invariantes matemáticas y entidades técnicas.
3. No resumas; cristaliza. Mantén la topología causal al 100%.
4. Salida: Solo el bloque refinado en texto plano. Cero explicaciones.

RUIDO TERMAL:
{content}

HECHO CRISTALIZADO:
"""


class AutoCrystallizer:
    """Refines low-exergy text into high-signal structural facts."""

    def __init__(self, llm_manager: LLMManager) -> None:
        self._llm = llm_manager

    async def crystallize(self, content: str, model_tag: str = "claude-fable-5") -> str:
        """
        Refines the input content via a zero-shot LLM loop to maximize exergy.

        Args:
            content: The raw text with potential thermal noise.
            model_tag: The LLM tier to use (defaults to SOTA compressor 'claude-fable-5').

        Returns:
            str: The refined, high-exergy fact.
        """
        logger.info("💎 [AURA-OMEGA] Crystallizing low-exergy fragment via %s...", model_tag)

        prompt = CRYSTALLIZATION_PROMPT.format(content=content)

        # Invoke the LLM with the crystallization instructions
        refined = await self._llm.generate(  # pyright: ignore[reportAttributeAccessIssue]
            prompt,
            model_tag=model_tag,
            temperature=0.0,  # Deterministic synthesis
            max_tokens=len(content) // 2 + 100,  # Enforce compression
        )

        refined = refined.strip()

        # If refinement failes or returns empty, raise hard exception to abort SAGA
        if not refined or len(refined) > len(content):
            logger.error("🛑 [SAGA-1] Crystallization failed to reduce entropy. Aborting pipeline.")
            raise RuntimeError(
                "[SAGA-1] Crystallization failed to reduce entropy. Aborting pipeline."
            )

        logger.info("✅ Fact crystallized: %d chars -> %d chars", len(content), len(refined))
        return refined
