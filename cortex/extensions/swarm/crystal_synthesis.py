# [C5-REAL] Exergy-Maximized
"""Crystal Synthesis Node.

Executes a deep synthesis of conflicting or redundant knowledge crystals.
Used by the CrystalConsolidator to fuse near-duplicate crystals while
preserving non-redundant information.

Axiom Ω₂: Entropic Asymmetry - Reducing noise by melting information together.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from cortex.extensions.llm._models import CortexPrompt
from cortex.extensions.llm.provider import LLMProvider
from cortex.extensions.llm.router import CortexLLMRouter, IntentProfile

logger = logging.getLogger("cortex_extensions.swarm.crystal_synthesis")

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
        "YOU ARE THE CORTEX SYNTHESIZER (AUTODIDACT-Ω).\n"
        "MODE: COGNITIVE CRYSTAL FUSION (Ω₂).\n\n"
        "You have two knowledge fragments that have been identified as redundant "
        "(>92% semantic similarity). Your task is to fuse them into a single diamond crystal "
        "that is dense, technical, and non-redundant.\n\n"
        "GOLDEN RULES:\n"
        "1. DO NOT LOSE DETAILS: If the secondary fragment has a detail, version, or flag that "
        "the primary one does not, include it.\n"
        "2. CUT THE FAT: Do not repeat ideas. If both say the same thing, synthesize it once.\n"
        "3. MAINTAIN TONE: Use dense, technical markdown.\n\n"
        "Respond in strict JSON format:\n"
        "{\n"
        '    "fused_content": "Synthesized markdown...",\n'
        '    "merged_entities": ["Entity 1", "Entity 2"],\n'
        '    "synthesis_logic": "Brief explanation of why they were fused."\n'
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
        err_val = result.unwrap_err()  # type: ignore[type-error]
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
