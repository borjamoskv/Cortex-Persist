"""
CORTEX v6 — Frontier Auditor (MODELOPFRONTERA).

Implementa la Tríada Soberana (TOM, OLIVER & BENJI) vía un LLM de frontera,
inyectando el contexto completo de un proyecto desde la DB local de CORTEX.
Axioma Ω₅ — Antifragile by Default.
"""

import logging
from typing import Any

from cortex.engine import CortexEngine
from cortex.llm.router import IntentProfile
from cortex.llm.sovereign import SovereignLLM

logger = logging.getLogger("cortex.audit.frontier")

_TOM_PROMPT = """Eres TOM (El Cuchillo) - CORTEX AUDIT.
Tu único objetivo es diseccionar el código y arquitectura provistos buscando vulnerabilidades críticas,
fugas de entropía (entropy leaks), deuda técnica masiva, asimetrías y bugs sutiles.
No ofrezcas soluciones amables. Extrae la sangre. Genera un reporte forense de hallazgos. Eres implacable.
Formato: Markdown estricto bajo el encabezado ## 🐺 HALLAZGOS (TOM).
"""

_BENJI_PROMPT = """Eres BENJI (El Escudo) - CORTEX AUDIT.
Recibes el contexto del proyecto y el reporte de sangre de TOM (El Cuchillo).
Tu trabajo es actuar como filtro ciego:
1. Evalúa si los hallazgos de TOM violan normativas (GDPR, SOX si aplican) o arquitectura CORTEX.
2. Descarta los falsos positivos o quejas puramente estilísticas de TOM.
3. Clasifica la materialidad de cada hallazgo verdadero.
Formato: Markdown estricto bajo el encabezado ## ⚖️ COMPLIANCE (BENJI).
"""

_OLIVER_PROMPT = """Eres OLIVER (El Martillo) - CORTEX AUDIT.
Recibes los hallazgos procesados por BENJI.
Tu mandato es emitir el Veredicto Inmutable.
1. Define el 'Score de Honor Ético' del código auditado (0 a 100). (Menos de 50 es CATASTRÓFICO).
2. Dicta los 'Efectos' y sentencias definitivas.
Aplica el formato Industrial Noir 2026.
Formato: Markdown estricto bajo el encabezado ## 🦅 VEREDICTO & EFECTOS (OLIVER).
"""


class FrontierAuditor:
    """Ejecuta una auditoría letal y exhaustiva de la frontera de CORTEX (Axioma Ω3 & Ω5)."""

    def __init__(self, engine: CortexEngine, model_override: str | None = None) -> None:
        self.engine = engine
        self._custom_model = model_override
        # Preferred models, ideally Google Gemini 1.5 Pro for massive context, or top-tier Qwen/Anthropic.
        self._preferred_providers = (
            [self._custom_model] if self._custom_model else ["gemini", "anthropic", "qwen"]
        )

    def _gather_project_context(self, project_name: str) -> str:
        """Extrae el estado arquitectónico y los facts actuales del proyecto."""
        logger.info("Gathering absolute context for project: %s", project_name)
        facts = self.engine.search_sync(query=f"project:{project_name}", top_k=100)

        if not facts:
            return f"[WARN]: No existen facts en CORTEX para el proyecto {project_name}."

        context_lines = []
        for f in facts:
            # We rely on DB schemas to pull fact context
            context_lines.append(f"- ID: {f.id} | Type: {f.type_name} | Content: {f.content}")

        return "\n".join(context_lines)

    async def run_audit(self, project_name: str) -> dict[str, Any]:
        """
        Inicia un ciclo cerrado de auditoría usando memoria soberana y la tríada distribuida.
        """
        logger.info("Frontier Auditor: Despertando Tríada Distribuida para [ %s ]...", project_name)

        project_context = self._gather_project_context(project_name)

        # 1. TOM (El Cuchillo) - Alta temperatura (0.7)
        prompt_tom = f"=== CONTEXTO DEL PROYECTO: {project_name} ===\n{project_context}\n\n=== MISIÓN TOM ===\nExtrae las vulnerabilidades y deuda técnica."
        async with SovereignLLM(
            preferred_providers=self._preferred_providers,
            timeout_seconds=120.0,
            use_orchestra=False,
            temperature=0.7,
        ) as tom_llm:
            tom_res = await tom_llm.generate(
                prompt=prompt_tom, system=_TOM_PROMPT, intent=IntentProfile.ARCHITECT
            )

        if not tom_res.ok:
            return {
                "status": "FALLBACK",
                "report_markdown": tom_res.content,
                "provider": tom_res.provider,
                "latency": tom_res.latency_ms,
            }

        # 2. BENJI (El Escudo) - Baja temperatura (0.1)
        prompt_benji = f"=== CONTEXTO DEL PROYECTO ===\n{project_context}\n\n=== HALLAZGOS TOM ===\n{tom_res.content}\n\n=== MISIÓN BENJI ===\nFiltra los falsos positivos y evalúa el compliance legal/arquitectónico."
        async with SovereignLLM(
            preferred_providers=self._preferred_providers,
            timeout_seconds=120.0,
            use_orchestra=False,
            temperature=0.1,
        ) as benji_llm:
            benji_res = await benji_llm.generate(
                prompt=prompt_benji, system=_BENJI_PROMPT, intent=IntentProfile.ARCHITECT
            )

        # 3. OLIVER (El Martillo) - Media temperatura (0.3)
        prompt_oliver = f"=== CONTEXTO DEL PROYECTO ===\n{project_context}\n\n=== DICTAMEN BENJI ===\n{benji_res.content}\n\n=== MISIÓN OLIVER ===\nEmite Veredicto Inmutable y Score."
        async with SovereignLLM(
            preferred_providers=self._preferred_providers,
            timeout_seconds=120.0,
            use_orchestra=False,
            temperature=0.3,
        ) as oliver_llm:
            oliver_res = await oliver_llm.generate(
                prompt=prompt_oliver, system=_OLIVER_PROMPT, intent=IntentProfile.ARCHITECT
            )

        # Reconstrucción del reporte final
        final_report = f"# 🛡️ FRONTIER AUDIT: {project_name}\n\n"
        final_report += f"{tom_res.content}\n\n"
        final_report += f"{benji_res.content}\n\n"
        final_report += f"{oliver_res.content}\n"

        # Persist to database
        self.engine.store_sync(
            tenant_id="default",
            project=project_name,
            fact_type="audit_report",
            content=final_report,
            confidence=0.95,
        )

        total_latency = tom_res.latency_ms + benji_res.latency_ms + oliver_res.latency_ms
        logger.info(
            "Tríada ejecutada con persistencia en DB (Latencia total: %.0fms)", total_latency
        )

        return {
            "status": "SUCCESS",
            "report_markdown": final_report,
            "provider": f"TOM({tom_res.provider}) -> BENJI({benji_res.provider}) -> OLIVER({oliver_res.provider})",
            "latency": total_latency,
        }

    async def synthesize_anomalies(self, alerts: list[Any]) -> dict[str, Any]:
        """
        Sintetiza anomalías de auto-auditoría en un diagnóstico táctico accionable.
        """
        if not alerts:
            return {"status": "SKIPPED", "report_markdown": ""}

        logger.info("Frontier Auditor: Synthesizing %s anomalies...", len(alerts))

        alert_details = "\n".join(
            f"- Issue: {getattr(a, 'issue', 'Unknown')} | Severity: {getattr(a, 'severity', 'Unknown')} | Message: {getattr(a, 'message', '')} | Metrics: {getattr(a, 'metrics', {})}"
            for a in alerts
        )

        prompt = (
            f"=== ANOMALÍAS DETECTADAS ===\n{alert_details}\n\n"
            "=== MISIÓN ===\n"
            "Analiza estas anomalías del sistema (fantasmas, errores acumulados) y genera 1 única \n"
            "directiva táctica corta y accionable para resolver el sangrado. \n"
            "No incluyas saludos. Usa el formato Industrial Noir 2026."
        )

        sys_prompt = "Eres el motor de auto-diagnóstico de CORTEX. Extrae el root cause y dicta cómo sanar la entropía."

        async with SovereignLLM(
            preferred_providers=self._preferred_providers,
            timeout_seconds=60.0,
            use_orchestra=False,
            temperature=0.2,
        ) as llm:
            res = await llm.generate(
                prompt=prompt, system=sys_prompt, intent=IntentProfile.ARCHITECT
            )

        if res.ok:
            # Persist to database as a diagnostic tip
            self.engine.store_sync(
                tenant_id="default",
                project="CORTEX",
                fact_type="diagnostic",
                content=res.content,
                confidence=0.85,
            )

        return {
            "status": "SUCCESS" if res.ok else "FALLBACK",
            "report_markdown": res.content,
            "provider": getattr(res, "provider", "unknown"),
        }
