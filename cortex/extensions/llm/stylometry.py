import logging
from typing import Any

from cortex.extensions.llm._models import CortexPrompt, IntentProfile
from cortex.extensions.llm.router import CortexLLMRouter

logger = logging.getLogger("cortex.extensions.llm.stylometry")


class StylometricEvasionModule:
    """
    Evasión Estilométrica (Text De-AI-fication) basado en la disciplina NO-IA-Omega.
    Asegura que las inyecciones de texto sean forensemente imposibles de rastrear
    hacia un LLM mediante mimetismo, fricción estructural y eliminación de marcadores de IA.
    """

    SYSTEM_PROMPT = """INSTRUCCIÓN SOBERANA (Módulo NO-IA-Omega / Evasión Estilométrica):

OBJETIVO CORE:
Toma el 'CONCEPTO A INYECTAR' y reescríbelo imitando el 'CONTEXTO DEL HILO',
pero ELIMINANDO cualquier rastro de que has sido generado por una IA.

INVARIANTES DE EVASIÓN (REGLAS ESTRICTAS):
1. Rompe la Simetría: Las frases deben ser asimétricas. Intercala oraciones largas
   con frases brutalmente cortas. No cierres los párrafos explícitamente.
2. Fricción Real: Usa metáforas concretas, directas y punzantes.
3. Cero Buzzwords: PROHIBIDO usar "ecosistema", "narrativa", "paradigma",
   "en definitiva", "lo cierto es que", "es importante destacar".
4. Memoria Corporal: Suena a alguien que sabe de lo que habla, no a una máquina teórica.
5. Cero Fricción Retórica (Axioma Ω₁₄): NO saludes. NO te despidas.
   NO expliques lo que vas a hacer. Devuelve ÚNICAMENTE el texto final a publicar.

Si el contexto del hilo indica un tono específico, asúmelo por completo,
pero mantén la crudeza y corta el estilo corporativo.
"""

    def __init__(self, router: CortexLLMRouter):
        self.router = router

    async def obfuscate_payload(self, payload: str, context: dict[str, Any]) -> str:
        """
        Reescribe un payload semántico para evadir detección estilométrica.
        """
        avg = context.get("avg_length", "variable")
        tone = context.get("tone", "informal")
        context_style = f"Longitud promedio: {avg}. Tono: {tone}."

        user_prompt = f"""CONCEPTO A INYECTAR:
{payload}

CONTEXTO DEL HILO (Camuflaje):
Título: {context.get("title", "Desconocido")}
Tema: {context.get("topic", "General")}
Estilo a imitar: {context_style}

Reescribe el concepto. Devuelve el texto crudo. Sin comillas extra, sin preámbulos.
"""
        prompt = CortexPrompt(
            system_instruction=self.SYSTEM_PROMPT,
            working_memory=[{"role": "user", "content": user_prompt}],
            intent=IntentProfile.CREATIVE,
            temperature=0.85,  # Alto para variabilidad y asimetría
            max_tokens=600,
        )

        logger.info("Aplicando evasión estilométrica al payload: %s...", payload[:30])
        result = await self.router.execute_resilient(prompt)

        if result.is_ok():
            return result.unwrap().strip()
        else:
            logger.error("Fallo en la evasión estilométrica: %s", result.error)
            return payload  # Fallback fail-open
