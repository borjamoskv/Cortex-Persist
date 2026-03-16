"""CORTEX v8.0 — Crystal Synthesis Node.

Executes a deep synthesis of conflicting or redundant knowledge crystals.
Used by the CrystalConsolidator to fuse near-duplicate crystals while
preserving non-redundant information.

Axiom Ω₂: Entropic Asymmetry — Reducing noise by melting information together.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from cortex.llm._models import CortexPrompt
from cortex.llm.provider import LLMProvider
from cortex.llm.router import CortexLLMRouter, IntentProfile

logger = logging.getLogger("cortex.swarm.crystal_synthesis")

_SYNTHESIS_PROVIDERS: tuple[str, ...] = (
    "qwen",
    "deepinfra",
    "groq",
    "together",
    "openrouter",
)

_synthesis_router: CortexLLMRouter | None = None


def _get_synthesis_router() -> CortexLLMRouter:
    global _synthesis_router
    if _synthesis_router is not None:
        return _synthesis_router

    primary: LLMProvider | None = None
    fallbacks: list[LLMProvider] = []

    for name in _SYNTHESIS_PROVIDERS:
        try:
            provider = LLMProvider(provider=name)
            if primary is None:
                primary = provider
            else:
                fallbacks.append(provider)
        except (ValueError, OSError, ImportError):
            continue

    if primary is None:
        raise RuntimeError("No LLM providers available for crystal synthesis.") from None

    _synthesis_router = CortexLLMRouter(primary, fallbacks)
    return _synthesis_router


async def synthesize_crystals(
    primary_content: str,
    secondary_content: str,
    context: str = "Semantic Merge",
) -> dict[str, Any]:
    """Execute a LLM-based synthesis of two conflicting or redundant crystals.

    Fuses the two contents into a single, dense, and non-redundant markdown.
    """
    logger.info("🧬 [SYNTHESIS] Fusing crystals... Context: %s", context)

    router = _get_synthesis_router()

    system_prompt = (
        "ERES EL SINTETIZADOR DE CORTEX (AUTODIDACT-Ω).\n"
        "MODO: FUSIÓN DE CRISTALES COGNITIVOS (Ω₂).\n\n"
        "Tienes dos fragmentos de conocimiento que han sido identificados como redundantes "
        "(>92% de similitud semántica). Tu tarea es fusionarlos en un único cristal de diamante "
        "que sea denso, técnico y sin redundancias.\n\n"
        "REGLAS DE ORO:\n"
        "1. NO PIERDAS DETALLES: Si el fragmento secundario tiene un detalle, versión o flag que "
        "el primario no tiene, inclúyelo.\n"
        "2. ELIMINA LA GRASA: No repitas ideas. Si ambos dicen lo mismo, sintetiza una vez.\n"
        "3. MANTÉN EL TONO: Usa markdown técnico y denso.\n\n"
        "Responde en formato JSON estricto:\n"
        "{\n"
        '    "fused_content": "Markdown sintetizado...",\n'
        '    "merged_entities": ["Entidad 1", "Entidad 2"],\n'
        '    "synthesis_logic": "Breve explicación de por qué se fusionaron."\n'
        "}"
    )

    prompt = CortexPrompt(
        system_instruction=system_prompt,
        working_memory=[
            {
                "role": "user",
                "content": (
                    f"PRIMARY CRYSTAL:\n{primary_content}\n\n"
                    f"SECONDARY CRYSTAL (REDUNDANT):\n{secondary_content}"
                ),
            }
        ],
        temperature=0.0,
        max_tokens=2000,
        intent=IntentProfile.REASONING,
        project="crystal_synthesis",
    )

    result = await router.execute_resilient(prompt)

    if result.is_err():
        err_val = result.unwrap_err()
        logger.error("❌ [SYNTHESIS] Failed to fuse crystals: %s", err_val)
        return {
            "fused_content": primary_content + "\n\n" + secondary_content,
            "error": str(err_val),
        }

    text_content = result.unwrap()
    try:
        json_match = re.search(r"\{.*\}", text_content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"fused_content": text_content}
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Error parsing fused crystal: %s", e)
        # Fallback to simple concatenation if JSON fails
        return {"fused_content": primary_content + "\n\n" + secondary_content, "error": str(e)}
