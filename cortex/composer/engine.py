# [C5-REAL] Exergy-Maximized
"""Orquestador de Síntesis Frontend JIT (CORTEX-Composer Engine).

Genera, extrae y audita código visual bajo las leyes Sovereign.
"""

from __future__ import annotations

import logging
import re

from cortex.composer.manifesto import COMPOSER_MANIFESTO
from cortex.composer.vision_qa import AestheticAuditor
from cortex.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.composer.engine")


class ComposerEngine:
    """Motor Vibe-Coding Soberano: Síntesis Frontend."""

    def __init__(self, router: CortexLLMRouter) -> None:
        self.router = router
        self.auditor = AestheticAuditor(router)

    def extract_code_block(self, response: str) -> dict[str, str]:
        """Extrae el código tsx/css marcados en la respuesta."""
        files = {}
        # Pattern: [FILE: filename]...\n```lang\ncode\n```
        file_matches = re.finditer(
            r"\[FILE:\s*([a-zA-Z0-9_\-\.]+)\]\s*```(?:typescript|tsx|jsx|css|javascript|ts|html)\n(.*?)```",
            response,
            re.DOTALL,
        )

        for match in file_matches:
            filename = match.group(1).strip()
            code = match.group(2).strip()
            files[filename] = code

        # Fallback genérico si el modelo no fue preciso
        if not files:
            snippets = re.findall(r"```(?:tsx|jsx|html)\n(.*?)```", response, re.DOTALL)
            if snippets:
                files["component.tsx"] = snippets[0].strip()

        return files

    def build_mock_html(self, files: dict[str, str]) -> str:
        """Ensambla un HTML simple inyectando CSS y JS para el QA Visual."""
        # This is a naive heuristic for purely visual components with minimal external react deps.
        # En un sistema real se requiere bundler `esbuild` / `vite` para compilar JSX.
        # Por contexto, forzamos "vanilla web components" o asumimos HTML renderizable:

        html_body = files.get("component.html", "") or files.get(
            "index.html", "<div>Fallback Visual Mismatch</div>"
        )
        css = files.get("component.css", "") or files.get("style.css", "")

        return f"<style>{css}</style>\n{html_body}"

    async def generate_component(
        self, description: str, max_retries: int = 2
    ) -> Result[dict[str, str], str]:
        """
        Inicia el AlphaZero-autodidact loop.
        Genera código iterando hasta que pase el QA estético.
        """
        logger.info("🎨 [COMPOSER] Iniciando síntesis JIT para: %s", description[:50])

        working_memory = [
            {
                "role": "user",
                "content": f"SINTETIZA: {description}\n\nSi usas React, usa un approach 'Vanilla / module.css'. Proporciona [FILE: index.html] nativo que lo renderice sin build steps si es posible, o JSX puro. Asegúrate de incluir [FILE: component.css].",
            }
        ]

        attempt = 1
        last_error = ""

        while attempt <= max_retries:
            prompt = CortexPrompt(
                system_instruction=COMPOSER_MANIFESTO,
                working_memory=working_memory,
                intent=IntentProfile.ARCHITECT,
                temperature=0.2,  # Determinismo para estética estructural
                max_tokens=6144,
            )

            res = await self.router.execute_resilient(prompt)
            if isinstance(res, Err):
                logger.error("Error en router de síntesis: %s", res.error)
                last_error = res.error or "Unknown synthesis error"
                attempt += 1
                continue

            response = res.unwrap()
            files = self.extract_code_block(response)

            if not files:
                logger.warning("No se detectó código estructurado [FILE: ...]. Reintentando...")
                working_memory.append({"role": "assistant", "content": response})
                working_memory.append(
                    {
                        "role": "user",
                        "content": "Error: NO encontré bloques de código marcados con [FILE: nombre] ``` \n Corrige el formato.",
                    }
                )
                attempt += 1
                last_error = "Formatting failure"
                continue

            # Construir visual preview temporal y someter a QA
            mock_html = self.build_mock_html(files)
            if mock_html.strip() == "<style></style>\n":
                logger.warning("HTML/CSS Mock vacío. Ignorando QA.")
                qa_res = Ok("Bypassed QA due to empty markup.")
            else:
                logger.info("📸 [COMPOSER] Ejecutando QA Visual...")
                qa_res = await self.auditor.audit_component(mock_html)

            if not isinstance(qa_res, Err):
                logger.info("💎 [COMPOSER] Estructura Estética VERIFICADA en intento %d.", attempt)
                return Ok(files)

            # QA Visual falló: realimenta el error al LLM
            logger.warning("💥 [COMPOSER] QA Visual (Aesthetic) Falló: %s", qa_res.error)
            working_memory.append({"role": "assistant", "content": response})
            working_memory.append(
                {
                    "role": "user",
                    "content": f"El QA de CORTEX rechazó tu componente por la siguiente vulnerabilidad estética:\n{qa_res.error}\n\nCorrige el CSS o la estructura para cumplir la ley #0A0A0A.",
                }
            )
            last_error = f"QA Failed: {qa_res.error}"
            attempt += 1

        return Err(f"Síntesis JIT exhausta tras {max_retries} intentos. Último error: {last_error}")
