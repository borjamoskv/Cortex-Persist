"""CORTEX MCP — Resilient Gateway Server.

Cascading URL fetcher with per-provider circuit breakers.
Complements Antigravity's browser_subagent when 503 errors block content extraction.

Axiom Ω₅: Antifragile by Default — the cascade never stops on a single failure.
Axiom Ω₃: Byzantine Default — verify HTTP response before trusting content.
"""

from __future__ import annotations

import asyncio
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

try:
    import aiohttp

    _HAS_AIOHTTP = True
except ImportError:
    aiohttp = None  # type: ignore[assignment]
    _HAS_AIOHTTP = False

import httpx

try:
    import markdownify

    _HAS_MARKDOWNIFY = True
except ImportError:
    markdownify = None  # type: ignore[assignment]
    _HAS_MARKDOWNIFY = False

try:
    from bs4 import BeautifulSoup

    _HAS_BS4 = True
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment]
    _HAS_BS4 = False

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None  # type: ignore

from cortex.utils.pulmones import CircuitBreaker, PulmonesQueue

logger = logging.getLogger("cortex.mcp.resilient_gateway")

# ─── Configuration ───────────────────────────────────────────────────

DEFAULT_TIMEOUT: float = 30.0
MAX_CONTENT_CHARS: int = 200_000
DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)
_HEADERS: dict[str, str] = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}


# ─── Cascade Event Telemetry ────────────────────────────────────────


@dataclass
class FetchCascadeEvent:
    """Telemetry event for a single cascade resolution."""

    url: str
    resolved_by: str | None
    depth: int
    latency_ms: float
    status_code: int | None = None
    errors: list[str] = field(default_factory=list)


# ─── Per-Provider Fetchers ──────────────────────────────────────────


async def _fetch_httpx(url: str, timeout: float) -> tuple[str, int]:
    """Primary: httpx async client with HTTP/2 support."""
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
        http2=True,
        headers=_HEADERS,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text, resp.status_code


async def _fetch_aiohttp(url: str, timeout: float) -> tuple[str, int]:
    """Fallback 1: aiohttp — different connection pool and HTTP stack."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(
        timeout=client_timeout,
        headers=_HEADERS,
    ) as session:
        async with session.get(url, allow_redirects=True) as resp:
            resp.raise_for_status()
            text = await resp.text()
            return text, resp.status


async def _fetch_urllib(url: str, timeout: float) -> tuple[str, int]:
    """Fallback 2: stdlib urllib — zero external deps, sync in executor."""
    loop = asyncio.get_running_loop()

    def _sync_fetch() -> tuple[str, int]:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace"), resp.status

    return await loop.run_in_executor(None, _sync_fetch)


# ─── Provider Registry ─────────────────────────────────────────────


@dataclass
class _FetchProvider:
    """A named fetch function with its own circuit breaker."""

    name: str
    fetch_fn: Any  # Callable[[str, float], Awaitable[tuple[str, int]]]
    circuit_breaker: CircuitBreaker = field(
        default_factory=lambda: CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    )


# ─── ResilientFetcher ───────────────────────────────────────────────


class ResilientFetcher:
    """Cascading URL fetcher with per-provider circuit breakers.

    Ω₅: Antifragile — cascades through independent HTTP stacks.
    Ω₃: Byzantine — validates status codes before trusting response body.
    """

    def __init__(self) -> None:
        self._providers: list[_FetchProvider] = [
            _FetchProvider(name="httpx", fetch_fn=_fetch_httpx),
            _FetchProvider(name="aiohttp", fetch_fn=_fetch_aiohttp),
            _FetchProvider(name="urllib", fetch_fn=_fetch_urllib),
        ]
        self._queue = PulmonesQueue()

    async def fetch(
        self,
        url: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        """Execute cascading fetch. Returns dict with content or error trace."""
        errors: list[str] = []
        start = time.time()

        for depth, provider in enumerate(self._providers, start=1):
            if not provider.circuit_breaker.can_execute():
                errors.append(f"{provider.name}: SKIP (circuit open)")
                continue

            try:
                prov_start = time.time()
                html, status_code = await asyncio.wait_for(
                    provider.fetch_fn(url, timeout),
                    timeout=timeout + 5.0,  # outer guard
                )
                latency_ms = (time.time() - prov_start) * 1000

                provider.circuit_breaker.record_success()

                logger.info(
                    "✅ [GATEWAY] %s resolved by %s (depth=%d, %.0fms, HTTP %s)",
                    url[:80],
                    provider.name,
                    depth,
                    latency_ms,
                    status_code,
                )

                markdown = _html_to_markdown(html)
                return {
                    "status": "success",
                    "content": markdown[:MAX_CONTENT_CHARS],
                    "provider": provider.name,
                    "cascade_depth": depth,
                    "latency_ms": round(latency_ms, 1),
                    "status_code": status_code,
                    "errors": errors,
                    "truncated": len(markdown) > MAX_CONTENT_CHARS,
                }

            except asyncio.TimeoutError:
                provider.circuit_breaker.record_failure()
                errors.append(f"{provider.name}: TIMEOUT ({timeout}s)")
                logger.warning("⏱️ [GATEWAY] %s timed out on %s", provider.name, url[:80])

            except Exception as e:  # noqa: BLE001 — catches all provider-specific HTTP errors
                provider.circuit_breaker.record_failure()
                error_msg = f"{provider.name}: {type(e).__name__}: {e}"
                errors.append(error_msg)
                logger.warning("❌ [GATEWAY] %s failed: %s", provider.name, error_msg)

            # Exponential backoff between providers (short: 0.5s, 1s)
            if depth < len(self._providers):
                await asyncio.sleep(0.5 * depth)

        # Total cascade failure — enqueue for deferred retry
        total_latency = (time.time() - start) * 1000
        self._queue.enqueue(
            "cortex.mcp.resilient_gateway.ResilientFetcher.fetch",
            (url,),
            {"timeout": timeout},
            delay=120.0,
        )
        logger.error(
            "💀 [GATEWAY] Cascade exhausted for %s. Errors: %s",
            url[:80],
            "; ".join(errors),
        )
        return {
            "status": "cascade_exhausted",
            "content": None,
            "errors": errors,
            "latency_ms": round(total_latency, 1),
        }


# ─── HTML → Markdown Conversion ────────────────────────────────────


def _html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown, stripping nav/script/style noise."""
    if not _HAS_BS4 or not _HAS_MARKDOWNIFY:
        # Fallback: basic tag stripping via regex
        import re

        text = re.sub(
            r"<(script|style|nav|footer|header|noscript|iframe)[^>]*>.*?</\1>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    soup = BeautifulSoup(html, "html.parser")

    # Strip noise elements (Ω₂: reduce entropy)
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()

    # Prefer <main> or <article> if present
    main = soup.find("main") or soup.find("article")
    target = main if main else soup

    return markdownify.markdownify(
        str(target),
        heading_style="ATX",
        strip=["img"],
    ).strip()


def _extract_with_selector(html: str, css_selector: str) -> str:
    """Extract content matching a CSS selector, then convert to markdown."""
    if not _HAS_BS4 or not _HAS_MARKDOWNIFY:
        return _html_to_markdown(html)

    soup = BeautifulSoup(html, "html.parser")
    elements = soup.select(css_selector)
    if not elements:
        return _html_to_markdown(html)  # Degrade gracefully

    combined = "\n\n".join(str(el) for el in elements)
    return markdownify.markdownify(combined, heading_style="ATX").strip()


# ─── Singleton Fetcher ──────────────────────────────────────────────

_fetcher: ResilientFetcher | None = None


def _get_fetcher() -> ResilientFetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = ResilientFetcher()
    return _fetcher


# ─── MCP Server Factory ────────────────────────────────────────────


def create_resilient_gateway(
    host: str = "127.0.0.1",
    port: int = 5002,
) -> FastMCP:
    """Create the Resilient Gateway FastMCP server."""
    if FastMCP is None:
        raise ImportError("FastMCP not available. Install with: pip install mcp")

    mcp = FastMCP(
        "CORTEX Resilient Gateway",
        host=host,
        port=port,
    )
    fetcher = _get_fetcher()

    @mcp.tool()
    async def resilient_fetch_url(
        url: str,
        timeout: float = 30.0,
        intent: str = "",
    ) -> str:
        """Fetch URL content with cascading fallback (httpx → aiohttp → urllib).

        Uses per-provider circuit breakers. Returns markdown-converted content.
        Use this when browser_subagent returns 503 or other transient errors.

        Args:
            url: The URL to fetch.
            timeout: Per-provider timeout in seconds (default 30).
            intent: Optional description of what you're looking for (for logging).
        """
        if intent:
            logger.info("🎯 [GATEWAY] Intent: %s", intent[:100])

        result = await fetcher.fetch(url, timeout=timeout)

        if result["status"] == "success":
            return (
                f"**Source:** {url}\n"
                f"**Provider:** {result['provider']} (depth {result['cascade_depth']})\n"
                f"**Latency:** {result['latency_ms']}ms\n\n"
                f"---\n\n{result['content']}"
            )

        return (
            f"❌ **Cascade exhausted** for {url}\n\n"
            f"**Errors:**\n"
            + "\n".join(f"- {e}" for e in result["errors"])
            + "\n\nThe request has been queued for deferred retry via PulmonesQueue."
        )

    @mcp.tool()
    async def resilient_read_page(
        url: str,
        css_selector: str = "",
        max_chars: int = 50_000,
        timeout: float = 30.0,
    ) -> str:
        """Fetch a page and extract targeted content with optional CSS filtering.

        Args:
            url: The URL to read.
            css_selector: Optional CSS selector to filter content (e.g. 'article', '.main-content').
            max_chars: Maximum characters to return (default 50000).
            timeout: Per-provider timeout in seconds (default 30).
        """
        result = await fetcher.fetch(url, timeout=timeout)

        if result["status"] != "success":
            return f"❌ Failed to fetch {url}: {'; '.join(result['errors'])}"

        raw_content = result["content"]

        # If a CSS selector was requested, re-parse from HTML
        # The content is already markdown, so we need the original HTML
        # We fetch again only if selector is given — but we can extract from
        # the markdown content directly for simple cases
        if css_selector:
            # Re-fetch raw HTML for selector extraction
            # This is a design trade-off: we cache the markdown but need HTML for selectors
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout),
                    follow_redirects=True,
                    headers=_HEADERS,
                ) as client:
                    resp = await client.get(url)
                    raw_content = _extract_with_selector(resp.text, css_selector)
            except httpx.RequestError:
                pass  # Degrade to full markdown content

        truncated = len(raw_content) > max_chars
        content = raw_content[:max_chars]

        suffix = "\n\n*[Content truncated]*" if truncated else ""
        return f"**Source:** {url}\n**Provider:** {result['provider']}\n\n---\n\n{content}{suffix}"

    return mcp


# ─── Standalone Entry Point ─────────────────────────────────────────


def run_resilient_gateway(
    host: str = "127.0.0.1",
    port: int = 5002,
    transport: str = "stdio",
) -> None:
    """Boot the Resilient Gateway MCP Server."""
    server = create_resilient_gateway(host=host, port=port)
    logger.info(
        "🛡️ [RESILIENT GATEWAY] Booting (transport=%s)",
        transport,
    )
    server.run(transport=transport)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_resilient_gateway()
