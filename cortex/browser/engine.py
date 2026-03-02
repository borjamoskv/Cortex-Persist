from typing import Any, Dict, List, Optional
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from cortex.utils.hygiene import LOG

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
        self._element_mapping: Dict[int, str] = {}  # Maps CORTEX ID to XPath or CSS selector

    async def start(self):
        """Initializes the browser context with stealth-like parameters."""
        LOG.debug("BROWSER: Starting Sovereign Engine...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--hide-scrollbars",
                "--mute-audio"
            ]
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self._page = await self._context.new_page()
        
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
            LOG.info(f"BROWSER: Navigating to {url}")
            await self._page.goto(url, wait_until="networkidle")
            return True
        except Exception as e:
            LOG.error(f"BROWSER: Navigation failed: {e}")
            return False

    async def parse_dom(self) -> str:
        """
        Injects a structural mapping script to attach cortex IDs to interactive elements.
        Returns a simplified DOM string for LLM digestion.
        """
        if not self._page:
            return ""

        # A Javascript snippet that locates all interactive or semantic elements,
        # sets a unique attribute `data-cortex-id`, and builds a simplified text representation.
        js_script = """
        () => {
            let idCounter = 1;
            const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [tabindex]:not([tabindex="-1"])';
            const elements = document.querySelectorAll(interactiveSelectors);
            let tree = [];
            
            elements.forEach((el) => {
                // Check visibility roughly
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0 || getComputedStyle(el).visibility === 'hidden') {
                    return;
                }
                
                // Assign ID
                const cortexId = idCounter++;
                el.setAttribute('data-cortex-id', cortexId);
                
                // Extract useful text
                let text = el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '';
                text = text.trim().replace(/\\n/g, ' ');
                
                if (text || el.tagName === 'INPUT') {
                    tree.push(`[${cortexId}] <${el.tagName.toLowerCase()}> ${text}`);
                }
            });
            
            return tree.join('\\n');
        }
        """
        simplified_dom = await self._page.evaluate(js_script)
        return simplified_dom

    async def click(self, cortex_id: int) -> bool:
        """Clicks an element by its CORTEX ID."""
        if not self._page:
            return False
        try:
            selector = f"[data-cortex-id='{cortex_id}']"
            await self._page.click(selector, timeout=5000)
            await self._page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            LOG.error(f"BROWSER: Failed to click element {cortex_id}: {e}")
            return False

    async def type(self, cortex_id: int, text: str) -> bool:
        """Types text into an element by its CORTEX ID."""
        if not self._page:
            return False
        try:
            selector = f"[data-cortex-id='{cortex_id}']"
            await self._page.fill(selector, text, timeout=5000)
            return True
        except Exception as e:
            LOG.error(f"BROWSER: Failed to type in element {cortex_id}: {e}")
            return False

    async def get_page_content(self) -> str:
        """Returns the raw page text (stripped of HTML) for context analysis."""
        if not self._page:
            return ""
        try:
            text = await self._page.evaluate("() => document.body.innerText")
            return text
        except Exception:
            return ""
