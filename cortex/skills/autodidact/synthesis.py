"""CORTEX AUTODIDACT-Ω — Sovereign Synthesis Pipeline.

Cristaliza radiación entrópica en Cristales Cognitivos usando el
CortexLLMRouter resiliente. Zero single-point-of-failure.

Axiom Ω₅: Antifragile by Default — el aprendizaje nunca se detiene por un 401.
"""

from typing import Any

import json
import logging
import os
import re
import time

from cortex.llm.provider import LLMProvider
from cortex.llm.router import CortexLLMRouter, IntentProfile
from cortex.llm._models import CortexPrompt
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.models import CortexFactModel
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2
from cortex.utils.pulmones import sovereign_circuit_breaker

logger = logging.getLogger("CORTEX.AUTODIDACT.SYNTHESIS")

# ==============================================================================
# 0. CONFIGURACIÓN SOBERANA (Ω₅: Antifragile by Default)
# ==============================================================================
ISOTHERMAL_THRESHOLD = 0.94  # Ω₂: Si es > 94% similar, Isoterma absoluta.
GRADIENT_THRESHOLD = 0.85  # Entre 0.85 y 0.94 entra en fricción dialéctica.

# Providers ordered by synthesis affinity (reasoning-heavy tasks)
_SYNTHESIS_PROVIDERS: tuple[str, ...] = (
    "qwen", "deepinfra", "groq", "together", "openrouter",
)

encode_engine = AsyncEncoder()
vector_db = SovereignVectorStoreL2(encoder=encode_engine)

# Lazy singleton — built on first use
_synthesis_router: CortexLLMRouter | None = None


def _get_synthesis_router() -> CortexLLMRouter:
    """Lazy-init the resilient synthesis router.

    Ω₅: Antifragile — tries every available provider.
    Ω₃: Byzantine Default — verifies key existence before trusting.
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
        raise RuntimeError(
            "No LLM providers available for synthesis. "
            "Configure at least one API key in .env"
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
@sovereign_circuit_breaker(timeout=10.0, max_retries=2)
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
            tenant_id="sovereign"
        )
        if nearest:
            similitud = getattr(nearest[0], "_recall_score", 0.0)
            if similitud > ISOTHERMAL_THRESHOLD:
                msg = (
                    "🛡️ [ENTROPIC SHIELD] ❄️ Zona Isoterma "
                    "Alcanzada (ΔS=%.4f)." % similitud
                )
                logger.warning(msg)
                return True, nearest[0].id
    except Exception as e:
        logger.error("Error checking redundancy L2: %s", e)

    return False, None


# ==============================================================================
# 2. EL CRISOL DE DESTILACIÓN (CortexLLMRouter Resiliente) -> Tier 🟢
# ==============================================================================
@sovereign_circuit_breaker(timeout=90.0, max_retries=1)
async def distill_sovereign_memo(
    raw_data: str, source_url: str, intent: str = ""
) -> dict[str, Any]:
    """Cristaliza el ruido térmico de la web en un Cristal Cognitivo a T=0K.

    Usa el CortexLLMRouter para cascade resiliente — si un provider falla,
    el siguiente toma el relevo. El intent_directive láser se preserva como
    el diferenciador sobre instruction grounding estándar.
    """
    logger.info(
        "🟢 [SYNTHESIS] Cristalización via Sovereign Router (Intent: %s)...",
        intent[:60] if intent else "GENERAL",
    )

    router = _get_synthesis_router()

    # ── Intent Directive Láser (El Diferenciador de CORTEX) ──
    intent_directive = (
        f"ENFOQUE LÁSER EN EL INTENT DEL AGENTE: '{intent}'. "
        "Filtra todo lo que no resuelva directa o indirectamente esta necesidad."
    ) if intent else "ENFOQUE GENERAL: Extracción de todos los patrones útiles."

    system_prompt = (
        "ERES AUTODIDACT-Ω. MODO: CRISTALIZACIÓN DE DIAMANTE (130/100).\n"
        "Tu directiva es convertir radiación entrópica en un fragmento "
        "de conocimiento soberano.\n"
        f"{intent_directive}\n\n"
        "LEYES DE SÍNTESIS:\n"
        "1. ZERO FLUFF: Elimina ruidos de navegación, anuncios y redundancias.\n"
        "2. ENTITY EXTRACTION: Identifica conceptos técnicos clave "
        "(G-Nodes), versiones y protocolos.\n"
        "3. AXIOMATIC RESONANCE: Describe cómo esta información expande "
        "los horizontes del sistema.\n\n"
        "Responde en formato JSON estricto:\n"
        '{\n'
        '    "content_markdown": "Texto destilado denso y técnico.",\n'
        '    "entities": ["Entidad A", "Protocolo B"],\n'
        '    "metadatos_extraidos": {"complexity": "tierra", "version": "1.0"},\n'
        '    "resonancia_axiomatica": "Impacto en Ω₀-Ω₆"\n'
        '}'
    )

    prompt = CortexPrompt(
        system_instruction=system_prompt,
        working_memory=[{
            "role": "user",
            "content": "SOURCE: %s\n\nRAW DATA:\n%s" % (
                source_url, raw_data[:180_000]
            ),
        }],
        temperature=0.0,
        max_tokens=4000,
        intent=IntentProfile.REASONING,
        project="autodidact_synthesis",
    )

    result = await router.execute_resilient(prompt)

    if result.is_err():
        logger.error("❌ [SYNTHESIS] Cascade exhausted: %s", result.error)
        return {"content_markdown": raw_data[:5000], "error": result.error}

    text_content = result.unwrap()

    try:
        json_match = re.search(r'\{.*\}', text_content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {
            "content_markdown": text_content,
            "entities": [],
            "resonancia_axiomatica": "Fail JSON"
        }
    except Exception as e:
        logger.error("Error parseando cristal: %s", e)
        return {"content_markdown": raw_data[:5000], "error": str(e)}


# ==============================================================================
# 3. EL PROTOCOLO TERMINAL (Integración AUTODIDACT-Ω)
# ==============================================================================
async def execute_cognitive_synthesis(
    raw_data: str, source: str, force: bool = False, intent: str = ""
) -> str:
    """Final del Pipeline: Verifica, Destila, Indexa."""
    is_redundant, existing_id = await check_semantic_redundancy(raw_data)
    if is_redundant and not force:
        logger.info("❄️ Isoterma detectada: %s", existing_id)
        return existing_id

    cristal = await distill_sovereign_memo(raw_data, source, intent)
    memo_content = cristal.get("content_markdown", "")
    entities = cristal.get("entities", [])
    resonancia = cristal.get("resonancia_axiomatica", "")

    bytes_in, bytes_out = len(raw_data), len(memo_content)
    rendimiento = (1 - (bytes_out / bytes_in)) * 100 if bytes_in > 0 else 0
    logger.info(
        "✅ Destilación: %.1f%% ruido eliminado. Entidades: %d",
        rendimiento, len(entities)
    )

    embed_result = await generate_cortex_embedding(memo_content)
    final_embedding = (
        embed_result if isinstance(embed_result, list)
        else await encode_engine.encode(memo_content)
    )

    memo_id = "MEMO_%s" % os.urandom(4).hex().upper()
    fact = CortexFactModel(
        id=memo_id,
        tenant_id="sovereign",
        project_id="autodidact_knowledge",
        content=memo_content,
        embedding=final_embedding,
        timestamp=time.time(),
        is_diamond=True,
        confidence="C5",
        cognitive_layer="synthesized_memo",
        metadata={
            "source": source,
            "tier": "sovereign_distilled",
            "entities": entities,
            "resonancia": resonancia
        }
    )

    await vector_db.memorize(fact)
    logger.info("✨ Singularidad Cognitiva grabada: %s", memo_id)
    return memo_id
