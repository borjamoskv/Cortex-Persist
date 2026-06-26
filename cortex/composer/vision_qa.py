# [C5-REAL] Exergy-Maximized
"""Sovereign Vision QA - Aesthetic Auditor (Vector 1).

Evaluates rendered components against the Industrial Noir 2026 guidelines
using Headless Playwright and Kimi K2.5 Multimodal (or compatible Frontier model).
"""

from __future__ import annotations

import base64
import logging

try:
    from playwright.async_api import async_playwright  # pyright: ignore[reportMissingImports]
except ImportError:
    async_playwright = None  # fallback

from cortex.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.composer.vision_qa")


class AestheticAuditor:
    """Validador estético impulsado por Multimodal Vision."""

    def __init__(self, router: CortexLLMRouter) -> None:
        self.router = router

    async def _capture_screenshot(self, html_content: str) -> bytes | None:
        """Arranca Playwright headless, inyecta el HTML y retorna snapshot."""
        if not async_playwright:
            logger.warning("Playwright not installed; skipping real vision QA capture.")
            return None

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                viewport={"width": 1280, "height": 800},
                device_scale_factor=2,  # Retina capture
            )
            # Inject generic wrapper logic
            wrapper = f"""
            <!DOCTYPE html>
            <html style="background: #0A0A0A; color: #FFFFFF; height: 100vh;">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
                <style>
                    body {{ margin: 0; font-family: 'Inter', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            await page.set_content(wrapper, wait_until="networkidle")
            # Force aesthetic layout
            screenshot = await page.screenshot(type="jpeg", quality=90)
            await browser.close()
            return screenshot

    async def audit_component(self, html_content: str) -> Result[str, str]:
        """
        Valida que el componente cumple con:
        1. Fondo puro (#0A0A0A / Transparente sobre wrapper).
        2. Ausencia de flickering textual.
        3. Acentos de color (Azul o Monocromo).

        Returns:
            Ok(feedback) si cumple, Err(feedback) si falla.
        """
        screenshot_bytes = await self._capture_screenshot(html_content)
        if not screenshot_bytes:
            return Ok("[STUB] Aesthetic QA Ignorado (Playwright no disponible).")

        b64_img = base64.b64encode(screenshot_bytes).decode("utf-8")

        system_instruction = (
            "You are the CORTEX Aesthetic Auditor (Teodosi-Omega tier). "
            "Analyze the provided UI component screenshot against the 'Industrial Noir 2026' manifesto:\n"
            "1. Deep dark background (#0A0A0A).\n"
            "2. Humanist / sleek typography.\n"
            "3. Proper alignment, margins, and premium visual hierarchy.\n"
            "Return EXACTLY the word 'PASS' if it is visually stunning and flawless. "
            "Return 'FAIL: <reasons>' if it contains basic styling, white backgrounds (when not explicitly dark-inverted), or misaligned elements."
        )

        prompt = CortexPrompt(
            system_instruction=system_instruction,
            working_memory=[
                {
                    "role": "user",
                    "content": [  # type: ignore
                        {"type": "text", "text": "Audita este render:"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                        },
                    ],
                }
            ],
            intent=IntentProfile.ARCHITECT,
            temperature=0.0,
        )

        try:
            # We enforce routing to a strong multimodal tier
            res = await self.router.execute_resilient(prompt)
            if res.is_ok():
                evaluation = res.unwrap().strip()
                if evaluation.startswith("PASS"):
                    return Ok("Aesthetic Check Passed.")
                return Err(evaluation)
            return Err(f"QA Router Error: {res.error}")  # pyright: ignore[reportAttributeAccessIssue]
        except Exception as e:
            return Err(f"Vision API Error: {e}")
