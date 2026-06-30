# [C5-REAL] Exergy-Maximized
"""CORTEX AUTODIDACT-Ω - Sovereign Synthesis Pipeline.

Cristaliza radiación entrópica en Cristales Cognitivos usando el
CortexLLMRouter resiliente. Zero single-point-of-failure.

Axiom Ω₅: Antifragile by Default - el aprendizaje nunca se detiene por un 401.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from babylon60.extensions.llm._models import CortexPrompt
from babylon60.extensions.llm.provider import LLMProvider
from babylon60.extensions.llm.router import CortexLLMRouter, IntentProfile
from babylon60.memory.encoder import AsyncEncoder
from babylon60.memory.models import CortexFactModel
from babylon60.memory.sqlite_vec_store import SovereignVectorStoreL2
from babylon60.utils.pulmones import sovereign_circuit_breaker
from babylon60.utils.turboquant import optimize_vector_qjl

logger = logging.getLogger("CORTEX.AUTODIDACT.SYNTHESIS")

# ==============================================================================
# 0. CONFIGURACIÓN SOBERANA (Ω₅: Antifragile by Default)
# ==============================================================================
ISOTHERMAL_THRESHOLD = 0.94  # Ω₂: Si es > 94% similar, Isoterma absoluta.
GRADIENT_THRESHOLD = 0.85  # Entre 0.85 y 0.94 entra en fricción dialéctica.

# LLM Synthesis Parameters
DEFAULT_SYNTHESIS_TEMPERATURE = 0.0
DEFAULT_SYNTHESIS_MAX_TOKENS = 4000
MAX_RAW_DATA_INPUT = 180_000
FALLBACK_CONTENT_LENGTH = 5000

# Timeouts and Retries
TIMEOUT_ENCODER = 10.0
TIMEOUT_DISTILL = 90.0
RETRIES_ENCODER = 2
RETRIES_DISTILL = 1

# Providers ordered by synthesis affinity (reasoning-heavy tasks)
_SYNTHESIS_PROVIDERS: tuple[str, ...] = (
    "ollama",
    "kimi",
    "perplexity",
    "openai",
    "groq",
    "gemini",
    "qwen",
    "deepinfra",
    "together",
    "openrouter",
)

encode_engine = AsyncEncoder()
vector_db = SovereignVectorStoreL2(encoder=encode_engine)

# Lazy singleton - built on first use
_synthesis_router: CortexLLMRouter | None = None


def _get_synthesis_router() -> CortexLLMRouter:
    """Lazy-init the resilient synthesis router.

    Ω₅: Antifragile - tries every available provider.
    Ω₃: Byzantine Default - verifies key existence before trusting.
    """
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
        except ValueError as e:
            logger.debug("Synthesis provider '%s' skipped: %s", name, e)

    if primary is None:
        logger.critical("🛑 [CORTEX] API KEY MISSING. Cannot synthesize without LLM.")
        raise RuntimeError(
            "No LLM providers available for synthesis. Configure at least one API key (e.g., GEMINI_API_KEY) in .env"
        )

    _synthesis_router = CortexLLMRouter(primary, fallbacks)
    logger.info(
        "🏗️ [SYNTHESIS ROUTER] Primary: %s | Fallbacks: %d",
        primary.provider_name,
        len(fallbacks),
    )
    return _synthesis_router


# ==============================================================================
# 1. LA MEMBRANA SEMÁNTICA (Native CORTEX Embeddings) -> Tier 🔵
# ==============================================================================
@sovereign_circuit_breaker(timeout=TIMEOUT_ENCODER, max_retries=RETRIES_ENCODER)
async def generate_cortex_embedding(text: str) -> list[float]:
    """Genera el embedding usando el motor nativo de CORTEX (384-dim)."""
    logger.info("🔵 [ENCODER] Calculando densidad semántica L2...")
    return await encode_engine.encode(text)


async def check_semantic_redundancy(text_snippet: str) -> tuple[bool, str | None]:
    """Axioma Ω₂: Si ya sabemos esto, aniquilamos la operación."""
    try:
        nearest = await vector_db.recall(
            query=text_snippet[:1000],
            limit=1,
            project="autodidact_knowledge",
            tenant_id="sovereign",
        )
        if nearest:
            similitud = getattr(nearest[0], "_recall_score", 0.0)
            if similitud > ISOTHERMAL_THRESHOLD:
                msg = f"🛡️ [ENTROPIC SHIELD] ❄️ Zona Isoterma Alcanzada (ΔS={similitud:.4f})."
                logger.warning(msg)
                return True, nearest[0].id
    except Exception as e:  # noqa: BLE001 - redundancy check failure must not crash synthesis
        logger.error("Error checking redundancy L2: %s", e)

    return False, None


# ==============================================================================
# 2. EL CRISOL DE DESTILACIÓN (CortexLLMRouter Resiliente) -> Tier 🟢
# ==============================================================================
@sovereign_circuit_breaker(timeout=TIMEOUT_DISTILL, max_retries=RETRIES_DISTILL)
async def distill_sovereign_memo(
    raw_data: str, source_url: str, intent: str = ""
) -> dict[str, Any]:
    """Cristaliza el ruido térmico de la web en un Cristal Cognitivo a T=0K.

    Usa el CortexLLMRouter para cascade resiliente - si un provider falla,
    el siguiente toma el relevo. El intent_directive láser se preserva como
    el diferenciador sobre instruction grounding estándar.
    """
    logger.info(
        "🟢 [SYNTHESIS] Crystallization via Sovereign Router (Intent: %s)...",
        intent[:60] if intent else "GENERAL",
    )

    router = _get_synthesis_router()

    # ── Laser Intent Directive (The CORTEX Differentiator) ──
    if intent:
        intent_directive = (
            f"LASER FOCUS ON THE AGENT INTENT: '{intent}'. "
            "Filter out any elements that do not directly or indirectly resolve this need."
        )
    else:
        intent_directive = "ENFOQUE GENERAL / GENERAL FOCUS: Extraction of all useful patterns."

    system_prompt = (
        "YOU ARE AUTODIDACT-Ω. MODE: DIAMOND CRYSTALLIZATION (130/100).\n"
        "Your directive is to convert entropic radiation into a fragment "
        "of sovereign knowledge.\n"
        f"{intent_directive}\n\n"
        "SYNTHESIS LAWS:\n"
        "1. ZERO FLUFF: Eliminate navigation noise, ads, and redundancies.\n"
        "2. STRUCTURAL EXTRACTION: You must extract EXACTLY 50 Primitivas and 50 Invariantes that maximize exergy.\n"
        "3. NEGATIVE SPACE: Identify Anti-patterns and Redundancies.\n"
        "4. ACTIONABLE: Provide Tips for immediate operational use.\n"
        "5. AXIOMATIC RESONANCE: Describe how this information expands "
        "the horizons of the system.\n\n"
        "Respond in strict JSON format:\n"
        "{\n"
        '    "content_markdown": "Dense and technical distilled text.",\n'
        '    "entities": ["Entity A", "Protocol B"],\n'
        '    "primitivas": ["Primitiva 1", "...", "Primitiva 50"],\n'
        '    "invariantes": ["Invariante 1", "...", "Invariante 50"],\n'
        '    "antipatrones": ["Antipatron 1", "...", "Antipatron N"],\n'
        '    "redundancias": ["Redundancia 1", "...", "Redundancia N"],\n'
        '    "tips": ["Tip 1", "...", "Tip N"],\n'
        '    "metadatos_extraidos": {"complexity": "land", "version": "1.0"},\n'
        '    "axiomatic_resonance": "Impact on Ω₀-Ω₆"\n'
        "}"
    )

    prompt = CortexPrompt(
        system_instruction=system_prompt,
        working_memory=[
            {
                "role": "user",
                "content": f"SOURCE: {source_url}\n\nRAW DATA:\n{raw_data[:MAX_RAW_DATA_INPUT]}",
            }
        ],
        temperature=DEFAULT_SYNTHESIS_TEMPERATURE,
        max_tokens=DEFAULT_SYNTHESIS_MAX_TOKENS,
        intent=IntentProfile.REASONING,
        project="autodidact_synthesis",
    )

    result = await router.execute_resilient(prompt)

    if result.is_err():
        logger.error("❌ [SYNTHESIS] Cascade exhausted: %s", result.error)  # type: ignore[union-attr]
        return {"content_markdown": raw_data[:FALLBACK_CONTENT_LENGTH], "error": result.error}  # type: ignore[union-attr]

    text_content = result.unwrap()

    try:
        json_match = re.search(r"\{.*\}", text_content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {
            "content_markdown": text_content,
            "entities": [],
            "axiomatic_resonance": "Fail JSON",
        }
    except Exception as e:  # noqa: BLE001 - parsing failure must fall back to raw content
        logger.error("Error parsing crystal: %s", e)
        return {"content_markdown": raw_data[:FALLBACK_CONTENT_LENGTH], "error": str(e)}


# ==============================================================================
# 3. THE TERMINAL PROTOCOL (AUTODIDACT-Ω Integration)
# ==============================================================================
async def execute_cognitive_synthesis(
    raw_data: str, source: str, force: bool = False, intent: str = ""
) -> str:
    """Pipeline End: Verify, Distill, Index."""
    is_redundant, existing_id = await check_semantic_redundancy(raw_data)
    if is_redundant and not force:
        logger.info("❄️ Isotherm detected: %s", existing_id)
        return existing_id or ""

    cristal_raw = await distill_sovereign_memo(raw_data, source, intent)
    if isinstance(cristal_raw, dict) and "status" in cristal_raw:
        cristal = cristal_raw.get("data", cristal_raw)
    else:
        cristal = cristal_raw

    if isinstance(cristal, dict):
        memo_content: str = cristal.get("content_markdown", "")
        entities: list[str] = cristal.get("entities", [])  # type: ignore[type-error]
        primitivas: list[str] = cristal.get("primitivas", [])
        invariantes: list[str] = cristal.get("invariantes", [])
        antipatrones: list[str] = cristal.get("antipatrones", [])
        redundancias: list[str] = cristal.get("redundancias", [])
        tips: list[str] = cristal.get("tips", [])
        resonancia: str = cristal.get("axiomatic_resonance", "")
    else:
        memo_content = str(cristal)
        entities = []
        primitivas = []
        invariantes = []
        antipatrones = []
        redundancias = []
        tips = []
        resonancia = ""

    bytes_in, bytes_out = len(raw_data), len(memo_content)
    yield_efficiency = (1 - (bytes_out / bytes_in)) * 100 if bytes_in > 0 else 0
    total_extracted = len(entities) + len(primitivas) + len(invariantes)
    logger.info("✅ Distillation: %.1f%% noise removed. Entities/Items: %d", yield_efficiency, total_extracted)

    # ── EPISTEMIC CONTRADICTION GUARD (Axioma Ω₁) ──
    from babylon60.guards.contradiction_guard import detect_contradictions

    conflict_report = await detect_contradictions(
        new_content=memo_content,
        new_project="autodidact_knowledge",
    )
    if conflict_report.has_conflicts and conflict_report.severity == "high":
        logger.error(
            "🛑 [EPISTEMIC SHOCK] Autodidact-Ω generated an assertion that directly "
            "contradicts the persisted memory (C5 Bypass Intercepted)."
        )
        for conflict in conflict_report.candidates[:3]:
            logger.error(
                "   Contradiction (score: %.3f) -> %s", conflict.overlap_score, conflict.fact_id
            )
        logger.error("Aborting crystallization to preserve thermodynamic integrity of the Tensor.")
        return f"REJECTED_EPISTEMIC_CONTRADICTION: {conflict_report.candidates[0].fact_id}"

    embed_result = await generate_cortex_embedding(memo_content)
    if isinstance(embed_result, list):
        base_embedding = embed_result
    else:
        base_embedding = await encode_engine.encode(memo_content)

    # Ingesting Axiom Ω₂ + TurboQuant (arXiv:2504.19874)
    final_embedding = optimize_vector_qjl(base_embedding, bits=3.5)

    memo_id = f"MEMO_{os.urandom(4).hex().upper()}"
    fact = CortexFactModel(
        id=memo_id,
        tenant_id="sovereign",
        project_id="autodidact_knowledge",
        content=memo_content,
        embedding=final_embedding,
        timestamp=time.monotonic(),
        is_diamond=True,
        confidence="C5",
        cognitive_layer="semantic",
        metadata={
            "source": source,
            "tier": "sovereign_distilled",
            "entities": entities,
            "primitivas": primitivas,
            "invariantes": invariantes,
            "antipatrones": antipatrones,
            "redundancias": redundancias,
            "tips": tips,
            "resonancia": resonancia,
            "quantization": "turboquant_3.5b_qjl",
            "compression_ratio": "absolute_neutrality_zero_indexing",
        },
    )

    await vector_db.memorize(fact)
    logger.info("✨ Cognitive Singularity written: %s", memo_id)
    return memo_id
