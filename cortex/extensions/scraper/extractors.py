"""SCRAPER-Ω — Multi-strategy extraction backends.

Each extractor implements the same interface: async extract(url) -> (title, content).
The ScraperEngine orchestrates fallback cascades between them.
"""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser

import httpx

LOG = logging.getLogger("cortex.extensions.scraper.extractors")

# ==============================================================================
# HTML-to-Markdown converter (zero external deps)
# ==============================================================================

_BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "section",
        "article",
        "main",
        "header",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "tr",
        "blockquote",
        "pre",
    }
)

_HEADING_MAP = {
    "h1": "# ",
    "h2": "## ",
    "h3": "### ",
    "h4": "#### ",
    "h5": "##### ",
    "h6": "###### ",
}

_SKIP_TAGS = frozenset({"script", "style", "noscript", "svg", "iframe", "nav", "footer"})


class _HtmlToMarkdown(HTMLParser):
    """Lightweight HTML-to-Markdown converter using stdlib only."""

    def __init__(self):
        super().__init__()
        self._output: list[str] = []
        self._skip_depth = 0
        self._tag_stack: list[str] = []
        self._title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        self._tag_stack.append(tag)

        if tag == "title":
            self._in_title = True
        elif tag in _HEADING_MAP:
            self._output.append("\n\n" + _HEADING_MAP[tag])
        elif tag == "br":
            self._output.append("\n")
        elif tag == "a":
            href = dict(attrs).get("href", "")
            self._output.append("[")
            self._tag_stack.append(f"__a_href:{href}")
        elif tag == "li":
            self._output.append("\n- ")
        elif tag in _BLOCK_TAGS:
            self._output.append("\n\n")
        elif tag == "strong" or tag == "b":
            self._output.append("**")
        elif tag == "em" or tag == "i":
            self._output.append("*")
        elif tag == "code":
            self._output.append("`")

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return

        if tag == "title":
            self._in_title = False
        elif tag == "a":
            # Pop the href marker
            href = ""
            while self._tag_stack and self._tag_stack[-1].startswith("__a_href:"):
                href = self._tag_stack.pop().split(":", 1)[1]
            self._output.append(f"]({href})")
        elif tag == "strong" or tag == "b":
            self._output.append("**")
        elif tag == "em" or tag == "i":
            self._output.append("*")
        elif tag == "code":
            self._output.append("`")
        elif tag in _BLOCK_TAGS:
            self._output.append("\n")

        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        if self._in_title:
            self._title = data.strip()
        self._output.append(data)

    def get_result(self) -> tuple[str, str]:
        """Returns (title, markdown_content)."""
        raw = "".join(self._output)
        # Collapse excessive whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", raw).strip()
        return self._title, cleaned


def html_to_markdown(html: str) -> tuple[str, str]:
    """Convert HTML to (title, markdown) using stdlib parser."""
    parser = _HtmlToMarkdown()
    parser.feed(html)
    return parser.get_result()


# ==============================================================================
# Extractor Protocol
# ==============================================================================


class BaseExtractor:
    """Base extractor interface."""

    async def extract(self, url: str, timeout: float = 15.0) -> tuple[str, str]:
        """Extract content from URL. Returns (title, markdown_content).

        Raises:
            ExtractionError: If extraction fails.
        """
        raise NotImplementedError


class ExtractionError(Exception):
    """Raised when an extraction strategy fails."""


# ==============================================================================
# 1. HTTP Fast Extractor (O(1) — raw httpx + stdlib HTML parser)
# ==============================================================================


class HttpExtractor(BaseExtractor):
    """Direct HTTP extraction with HTML-to-Markdown conversion.

    Fastest strategy. Works for static HTML pages.
    Fails on JS-rendered SPAs and sites with aggressive anti-bot.
    """

    async def extract(self, url: str, timeout: float = 15.0) -> tuple[str, str]:
        LOG.info("🔵 [HTTP_FAST] Extracting: %s", url)
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    raise ExtractionError(f"Non-HTML content type: {content_type}")

                title, markdown = html_to_markdown(response.text)
                if not markdown or len(markdown) < 50:
                    raise ExtractionError("Extracted content too short — likely JS-rendered SPA")
                return title, markdown

        except httpx.HTTPStatusError as e:
            raise ExtractionError(f"HTTP {e.response.status_code} for {url}") from e
        except httpx.RequestError as e:
            raise ExtractionError(f"Network error for {url}: {e}") from e


# ==============================================================================
# 2. Jina Reader Extractor (Tier 🔵 — API-based markdown)
# ==============================================================================


class JinaExtractor(BaseExtractor):
    """Jina Reader API — converts any URL to clean markdown.

    No API key required for basic usage. Handles JS rendering server-side.
    """

    JINA_ENDPOINT = "https://r.jina.ai"

    async def extract(self, url: str, timeout: float = 15.0) -> tuple[str, str]:
        LOG.info("🟡 [JINA] Extracting: %s", url)
        import os

        target = f"{self.JINA_ENDPOINT}/{url}"
        headers: dict[str, str] = {"Accept": "text/markdown"}
        api_key = os.environ.get("JINA_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(target, headers=headers)
                response.raise_for_status()
                content = response.text.strip()
                if not content or len(content) < 30:
                    raise ExtractionError("Jina returned empty or minimal content")

                # Extract title from first markdown heading
                title = ""
                for line in content.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

                return title, content

        except httpx.HTTPStatusError as e:
            raise ExtractionError(f"Jina HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise ExtractionError(f"Jina network error: {e}") from e


# ==============================================================================
# 3. Firecrawl Extractor (Tier 🟢 — deep crawl)
# ==============================================================================


class FirecrawlExtractor(BaseExtractor):
    """Firecrawl API — deep extraction with JS rendering.

    Requires FIRECRAWL_API_KEY environment variable.
    """

    FIRECRAWL_ENDPOINT = "https://api.firecrawl.dev/v1/scrape"

    async def extract(self, url: str, timeout: float = 20.0) -> tuple[str, str]:
        LOG.info("🟢 [FIRECRAWL] Extracting: %s", url)
        import os

        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key:
            raise ExtractionError("FIRECRAWL_API_KEY not set")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.FIRECRAWL_ENDPOINT, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                if not data.get("success"):
                    raise ExtractionError(
                        f"Firecrawl extraction unsuccessful: {data.get('error', 'unknown')}"
                    )

                result_data = data.get("data", {})
                content = result_data.get("markdown", "")
                title = result_data.get("metadata", {}).get("title", "")

                if not content:
                    raise ExtractionError("Firecrawl returned empty markdown")

                return title, content

        except httpx.HTTPStatusError as e:
            raise ExtractionError(f"Firecrawl HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise ExtractionError(f"Firecrawl network error: {e}") from e


# ==============================================================================
# 4. Playwright Extractor (Tier 🔴 — full browser rendering)
# ==============================================================================


class PlaywrightExtractor(BaseExtractor):
    """Playwright-based extraction — full browser rendering.

    Heaviest strategy. Use as last resort for heavily JS-rendered SPAs.
    Leverages cortex.browser.BrowserEngine.
    """

    async def extract(self, url: str, timeout: float = 30.0) -> tuple[str, str]:
        LOG.info("🔴 [PLAYWRIGHT] Extracting: %s", url)
        try:
            from cortex.extensions.browser.engine import BrowserEngine

            engine = BrowserEngine(headless=True)
            await engine.start()
            try:
                await engine.goto(url)
                content = await engine.get_page_content()
                # Extract title from page
                title = await engine._page.title() if engine._page else ""
                if not content or len(content) < 30:
                    raise ExtractionError("Playwright extracted empty content")
                return title, content
            finally:
                await engine.stop()

        except ImportError as e:
            raise ExtractionError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            ) from e
        except RuntimeError as e:
            raise ExtractionError(f"Playwright engine error: {e}") from e


# ==============================================================================
# 5. Robots.txt Checker
# ==============================================================================


async def check_robots_txt(url: str, timeout: float = 5.0) -> bool:
    """Check if a URL is allowed by robots.txt.

    Returns True if scraping is allowed, False if blocked.
    On error (no robots.txt, network failure), defaults to allowed.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    path = parsed.path or "/"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(robots_url)
            if response.status_code != 200:
                return True  # No robots.txt = allowed

            # Simple robots.txt parser for User-agent: * rules
            lines = response.text.split("\n")
            applies = False
            for line in lines:
                line = line.strip().lower()
                if line.startswith("user-agent:"):
                    agent = line.split(":", 1)[1].strip()
                    applies = agent == "*"
                elif applies and line.startswith("disallow:"):
                    disallowed = line.split(":", 1)[1].strip()
                    if disallowed and path.startswith(disallowed):
                        LOG.warning(
                            "🚫 [ROBOTS] Path %s blocked by robots.txt rule: Disallow: %s",
                            path,
                            disallowed,
                        )
                        return False

            return True

    except (httpx.RequestError, OSError):
        return True  # Network error = assume allowed


# ==============================================================================
# Extractor Registry
# ==============================================================================

EXTRACTORS: dict[str, BaseExtractor] = {
    "http_fast": HttpExtractor(),
    "jina": JinaExtractor(),
    "firecrawl": FirecrawlExtractor(),
    "playwright": PlaywrightExtractor(),
}

# Default cascade order for AUTO strategy
CASCADE_ORDER = ["http_fast", "jina", "firecrawl", "playwright"]
