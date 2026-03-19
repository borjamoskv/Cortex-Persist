"""
CORTEX v6 — Frontier Auditor (MODELOPFRONTERA).

Implementa la Tríada Soberana (TOM, OLIVER & BENJI) vía un LLM de frontera,
inyectando el contexto completo de un proyecto desde la DB local de CORTEX.
Axioma Ω₅ — Antifragile by Default.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.engine import CortexEngine
from cortex.extensions.llm.router import IntentProfile
from cortex.extensions.llm.sovereign import SovereignLLM

logger = logging.getLogger("cortex.audit.frontier")

# ─── Agent Prompts ────────────────────────────────────────────────────

_TOM_PROMPT = (
    "Eres TOM (El Cuchillo) - CORTEX AUDIT.\n"
    "Tu único objetivo es diseccionar el código y arquitectura "
    "provistos buscando vulnerabilidades críticas, fugas de "
    "entropía (entropy leaks), deuda técnica masiva, asimetrías "
    "y bugs sutiles.\n"
    "No ofrezcas soluciones amables. Extrae la sangre. "
    "Genera un reporte forense de hallazgos. Eres implacable.\n"
    "Formato: Markdown estricto bajo el encabezado "
    "## 🐺 HALLAZGOS (TOM)."
)

_BENJI_PROMPT = (
    "Eres BENJI (El Escudo) - CORTEX AUDIT.\n"
    "Recibes el contexto del proyecto y el reporte de TOM.\n"
    "Tu trabajo es actuar como filtro ciego:\n"
    "1. Evalúa si los hallazgos de TOM violan normativas "
    "(GDPR, SOX si aplican) o arquitectura CORTEX.\n"
    "2. Descarta los falsos positivos o quejas estilísticas.\n"
    "3. Clasifica la materialidad de cada hallazgo verdadero.\n"
    "Formato: Markdown estricto bajo el encabezado "
    "## ⚖️ COMPLIANCE (BENJI)."
)

_OLIVER_PROMPT = (
    "Eres OLIVER (El Martillo) - CORTEX AUDIT.\n"
    "Recibes los hallazgos procesados por BENJI.\n"
    "Tu mandato es emitir el Veredicto Inmutable.\n"
    "1. Define el 'Score de Honor Ético' del código "
    "auditado (0 a 100). Menos de 50 es CATASTRÓFICO.\n"
    "2. Dicta los 'Efectos' y sentencias definitivas.\n"
    "Aplica el formato Industrial Noir 2026.\n"
    "Formato: Markdown estricto bajo el encabezado "
    "## 🦅 VEREDICTO & EFECTOS (OLIVER)."
)


class FrontierAuditor:
    """Ejecuta una auditoría letal de la frontera de CORTEX."""

    def __init__(
        self,
        engine: CortexEngine,
        model_override: str | None = None,
        timeout: float = 120.0,
        persist: bool = True,
    ) -> None:
        self.engine = engine
        self._custom_model = model_override
        self._timeout = timeout
        self._persist = persist
        self._preferred_providers = (
            [self._custom_model]
            if self._custom_model
            else ["gemini", "anthropic", "qwen"]
        )

    async def _gather_project_context(
        self, project_name: str
    ) -> str:
        """Extrae el estado arquitectónico del proyecto."""
        logger.info(
            "Gathering context for project: %s", project_name
        )
        facts = await self.engine.search(
            query=f"project:{project_name}", top_k=100
        )

        if not facts:
            return (
                f"[WARN]: No facts in CORTEX for "
                f"project {project_name}."
            )

        lines = []
        for f in facts:
            lines.append(
                f"- ID: {f.fact_id} | "
                f"Type: {f.fact_type} | "
                f"Content: {f.content}"
            )
        return "\n".join(lines)

    async def _run_agent(
        self,
        name: str,
        system: str,
        prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        """Run a single triad agent. Never raises."""
        try:
            async with SovereignLLM(
                preferred_providers=self._preferred_providers,
                timeout_seconds=self._timeout,
                use_orchestra=False,
                temperature=temperature,
            ) as llm:
                res = await llm.generate(
                    prompt=prompt,
                    system=system,
                    intent=IntentProfile.ARCHITECT,
                )
            return {
                "ok": res.ok,
                "content": res.content,
                "provider": res.provider,
                "latency_ms": res.latency_ms,
                "chain": res.fallback_chain,
                "errors": res.error_log,
            }
        except Exception as e:
            logger.exception("Agent %s crashed", name)
            return {
                "ok": False,
                "content": f"[{name} CRASHED]: {e}",
                "provider": "error",
                "latency_ms": 0.0,
                "chain": [],
                "errors": [str(e)],
            }

    async def run_audit(
        self, project_name: str
    ) -> dict[str, Any]:
        """Inicia la auditoría con la tríada distribuida."""
        logger.info(
            "Frontier Auditor: awakening triad for [%s]...",
            project_name,
        )

        ctx = await self._gather_project_context(project_name)

        # ── 1. TOM (El Cuchillo) — temp 0.7 ──────────────
        tom = await self._run_agent(
            "TOM",
            _TOM_PROMPT,
            (
                f"=== CONTEXTO: {project_name} ===\n{ctx}\n\n"
                "=== MISIÓN TOM ===\n"
                "Extrae vulnerabilidades y deuda técnica."
            ),
            temperature=0.7,
        )

        if not tom["ok"]:
            return {
                "status": "FALLBACK",
                "report_markdown": tom["content"],
                "provider": tom["provider"],
                "latency": tom["latency_ms"],
                "errors": tom["errors"],
            }

        # ── 2. BENJI (El Escudo) — temp 0.1 ─────────────
        benji = await self._run_agent(
            "BENJI",
            _BENJI_PROMPT,
            (
                f"=== CONTEXTO ===\n{ctx}\n\n"
                f"=== HALLAZGOS TOM ===\n{tom['content']}\n\n"
                "=== MISIÓN BENJI ===\n"
                "Filtra falsos positivos y evalúa compliance."
            ),
            temperature=0.1,
        )

        # ── 3. OLIVER (El Martillo) — temp 0.3 ──────────
        oliver = await self._run_agent(
            "OLIVER",
            _OLIVER_PROMPT,
            (
                f"=== CONTEXTO ===\n{ctx}\n\n"
                f"=== DICTAMEN BENJI ===\n{benji['content']}\n\n"
                "=== MISIÓN OLIVER ===\n"
                "Emite Veredicto Inmutable y Score."
            ),
            temperature=0.3,
        )

        # ── Build final report ───────────────────────────
        final_report = (
            f"# 🛡️ FRONTIER AUDIT: {project_name}\n\n"
            f"{tom['content']}\n\n"
            f"{benji['content']}\n\n"
            f"{oliver['content']}\n"
        )

        # ── Persist ──────────────────────────────────────
        if self._persist:
            try:
                await self.engine.store(
                    tenant_id="default",
                    project=project_name,
                    fact_type="audit_report",
                    content=final_report,
                    confidence=0.95,
                )
            except Exception as e:
                logger.warning("Failed to persist audit: %s", e)

        total_latency = (
            tom["latency_ms"]
            + benji["latency_ms"]
            + oliver["latency_ms"]
        )
        providers = (
            f"TOM({tom['provider']}) → "
            f"BENJI({benji['provider']}) → "
            f"OLIVER({oliver['provider']})"
        )

        logger.info(
            "Triad executed (%.0fms total)", total_latency
        )

        return {
            "status": "SUCCESS",
            "report_markdown": final_report,
            "provider": providers,
            "latency": total_latency,
            "errors": (
                tom["errors"] + benji["errors"] + oliver["errors"]
            ),
        }

    async def synthesize_anomalies(
        self, alerts: list[Any]
    ) -> dict[str, Any]:
        """Sintetiza anomalías en un diagnóstico accionable."""
        if not alerts:
            return {"status": "SKIPPED", "report_markdown": ""}

        logger.info(
            "Synthesizing %s anomalies...", len(alerts)
        )

        details = "\n".join(
            f"- Issue: {getattr(a, 'issue', '?')} | "
            f"Severity: {getattr(a, 'severity', '?')} | "
            f"Message: {getattr(a, 'message', '')} | "
            f"Metrics: {getattr(a, 'metrics', {})}"
            for a in alerts
        )

        prompt = (
            f"=== ANOMALÍAS DETECTADAS ===\n{details}\n\n"
            "=== MISIÓN ===\n"
            "Analiza estas anomalías y genera 1 directiva "
            "táctica corta y accionable. Sin saludos. "
            "Formato Industrial Noir 2026."
        )
        sys_prompt = (
            "Eres el motor de auto-diagnóstico de CORTEX. "
            "Extrae el root cause y dicta cómo sanar."
        )

        result = await self._run_agent(
            "DIAGNOSTICS", sys_prompt, prompt, temperature=0.2
        )

        if result["ok"] and self._persist:
            try:
                await self.engine.store(
                    tenant_id="default",
                    project="CORTEX",
                    fact_type="diagnostic",
                    content=result["content"],
                    confidence=0.85,
                )
            except Exception as e:
                logger.warning("Failed to persist diag: %s", e)

        return {
            "status": "SUCCESS" if result["ok"] else "FALLBACK",
            "report_markdown": result["content"],
            "provider": result["provider"],
        }
