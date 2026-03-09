import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

# Importación de la Cúspide O(1)
from cortex.skills.autodidact.actuator import autodidact_pipeline

logger = logging.getLogger("CORTEX.TOOLS.AUTODIDACT")

class AutodidactIngestionArgs(BaseModel):
    target: str = Field(
        ..., 
        description="URL absoluta de la documentación, Query directa (ej: 'how React compiler works'), o enlace de Audio."
    )
    intent: str = Field(
        ...,
        description="Modo de ingesta. 'quick_read' (URL simple a Markdown), 'deep_learn' (Scrape recursivo de docs web), 'search_gap' (Busca la info en la web para una Query), o 'audio_ingest' (Música/Audio a texto)."
    )
    force: bool = Field(
        default=False,
        description="True para forzar la asimilación ignorando si ya existe un memo semánticamente idéntico en CORTEX."
    )

class AutodidactIngestionTool:
    """
    Herramienta O O Muerte para que cualquier agente CORTEX dispare 
    el motor de adquisición cognitiva (AUTODIDACT-Ω) ante un vacío de conocimiento.
    """
    name: str = "autodidact_cognitive_ingestion"
    description: str = (
        "Úsalo cuando detectes que te falta contexto técnico crítico (ej. nueva API, docs de framework). "
        "Adquiere, destila y graba el conocimiento permanentemente en la Memoria CORTEX."
    )
    args_schema = AutodidactIngestionArgs

    async def _arun(self, target: str, intent: str, force: bool = False) -> str:
        """La ejecución asíncrona inmaterial."""
        logger.info("🧠 [AGENT TOOL] Disparando AUTODIDACT-Ω -> Target: %s | Intent: %s", target, intent)
        try:
            # Invoca el pipeline completo. Como está protegido por PULMONES, 
            # el agente principal nunca se bloqueará si la red cae.
            await autodidact_pipeline(target, intent, force)
            
            # Devolvemos un string limpio para el scratchpad del LLM.
            return (
                f"Protocolo AUTODIDACT ejecutado sobre '{target}' con intent '{intent}'. "
                f"El conocimiento ha sido/será destilado y sembrado en cortex.db (vía PULMONES si hubo fallo de red)."
            )
        except Exception as e:
            logger.error("Falla crítica en herramienta Autodidact: %s", e)
            return f"❌ ERROR DE INGESTA COGNITIVA: {str(e)}."

    def _run(self, *args, **kwargs) -> Any:
        raise NotImplementedError("AUTODIDACT-Ω es puramente asíncrono (PULMONES). Usa _arun.")
