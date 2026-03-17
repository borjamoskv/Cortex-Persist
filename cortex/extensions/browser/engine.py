from __future__ import annotations

import logging
from typing import Any, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

LOG = logging.getLogger("cortex.extensions.browser")


class BrowserEngine:
    """
    Sovereign Browser Engine for CORTEX.
    Leverages Playwright for autonomous web interaction.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._element_mapping: dict[int, str] = {}  # Maps CORTEX ID to XPath or CSS selector

    async def start(self):
        """Initializes the browser context with stealth-like parameters."""
        LOG.debug("BROWSER: Starting Sovereign Engine...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--hide-scrollbars",
                "--mute-audio",
            ],
        )
        if not self._browser:
            raise RuntimeError("Browser failed to launch.")
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        if not self._context:
            raise RuntimeError("Context failed to create.")
        self._page = await self._context.new_page()

        assert self._page is not None
        # Override navigator.webdriver
        await self._page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        LOG.info("BROWSER: Engine active.")

    async def stop(self):
        """Tears down the browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        LOG.debug("BROWSER: Engine shut down.")

    async def goto(self, url: str) -> bool:
        """Navigates to a specific URL."""
        if not self._page:
            raise RuntimeError("Browser Engine not started.")
        try:
            LOG.info("BROWSER: Navigating to %s", url)
            await self._page.goto(url, wait_until="networkidle")
            return True
        except Exception as e:  # noqa: BLE001
            LOG.error("BROWSER: Navigation failed: %s", e)
            raise RuntimeError(f"BROWSER: Navigation to {url} failed: {e}") from e

    async def parse_dom(self) -> dict[str, Any]:
        """
        Injects a structural mapping script to attach cortex IDs to interactive elements.
        Returns a dict with the simplified DOM string for LLM digestion
        and metrics of discarded elements.
        """
        if not self._page:
            return {"dom": "", "stats": {}}

        # A Javascript snippet that locates all interactive or semantic elements,
        # sets a unique attribute `data-cortex-id`, and builds a simplified text representation.
        js_script = """
        () => {
            let idCounter = 1;
            const interactiveSelectors = [
                'a', 'button', 'input', 'select', 'textarea',
                '[role="button"]', '[role="link"]',
                '[tabindex]:not([tabindex="-1"])'
            ].join(', ');
            const elements = document.querySelectorAll(interactiveSelectors);
            let tree = [];
            let stats = {
                total: elements.length,
                discarded_size: 0,
                discarded_visibility: 0,
                discarded_opacity: 0,
                accepted: 0
            };
            
            elements.forEach((el) => {
                const rect = el.getBoundingClientRect();
                const computed = getComputedStyle(el);
                let discarded = false;

                if (rect.width === 0 || rect.height === 0) {
                    stats.discarded_size++;
                    discarded = true;
                } else if (computed.visibility === 'hidden' || computed.display === 'none') {
                    stats.discarded_visibility++;
                    discarded = true;
                } else if (computed.opacity === '0') {
                    stats.discarded_opacity++;
                    discarded = true;
                }

                if (discarded) return;
                
                // Assign ID
                const cortexId = idCounter++;
                el.setAttribute('data-cortex-id', cortexId);
                
                // Extract useful text
                let text = el.innerText || el.value || el.placeholder || 
                           el.getAttribute('aria-label') || '';
                text = text.trim().replace(/\\n/g, ' ');
                if (text || el.tagName === 'INPUT') {
                    tree.push(`[${cortexId}] <${el.tagName.toLowerCase()}> ${text}`);
                    stats.accepted++;
                }
            });
            
            return {
                dom: tree.join('\\n'),
                stats: stats
            };
        }
        """
        result = await self._page.evaluate(js_script)

        stats = result.get("stats", {})
        total = stats.get("total", 0)
        accepted = stats.get("accepted", 0)

        LOG.debug(
            "BROWSER: DOM Analizado. Total: %d | Aceptados: %d | Descartados: %d"
            " (Size: %s, Vis: %s, Op: %s)",
            total,
            accepted,
            total - accepted,
            stats.get("discarded_size"),
            stats.get("discarded_visibility"),
            stats.get("discarded_opacity"),
        )

        # Asimetría Semántica: Alarma de 2º orden
        if total > 50:
            discard_ratio = (total - accepted) / total
            if discard_ratio > 0.8:
                LOG.warning(
                    "BROWSER: ⚠️ Ceguera Adversaria Detectada. %.1f%% de elementos "
                    "(%d/%d) fueron ignorados por filtros de visibilidad. "
                    "Posible UI hostil o mal empaquetada.",
                    discard_ratio * 100,
                    total - accepted,
                    total,
                )

        return result

    async def click(self, cortex_id: int) -> bool:
        """Clicks an element by its CORTEX ID."""
        if not self._page:
            return False
        try:
            selector = f"[data-cortex-id='{cortex_id}']"
            await self._page.click(selector, timeout=5000)
            await self._page.wait_for_load_state("networkidle")
            return True
        except Exception as e:  # noqa: BLE001
            LOG.error("BROWSER: Failed to click element %s: %s", cortex_id, e)
            raise RuntimeError(f"BROWSER: Click operation failed on node {cortex_id}: {e}") from e

    async def type(self, cortex_id: int, text: str) -> bool:
        """Types text into an element by its CORTEX ID."""
        if not self._page:
            return False
        try:
            selector = f"[data-cortex-id='{cortex_id}']"
            await self._page.fill(selector, text, timeout=5000)
            return True
        except Exception as e:  # noqa: BLE001
            LOG.error("BROWSER: Failed to type in element %s: %s", cortex_id, e)
            raise RuntimeError(f"BROWSER: Type operation failed on node {cortex_id}: {e}") from e

    async def get_page_content(self) -> str:
        """Returns the raw page text (stripped of HTML) for context analysis."""
        if not self._page:
            return ""
        try:
            text = await self._page.evaluate("() => document.body.innerText")
            return text
        except Exception as e:  # noqa: BLE001
            LOG.error("BROWSER: Failed to extract page content: %s", e)
            raise RuntimeError(f"BROWSER: Page content extraction failed: {e}") from e
