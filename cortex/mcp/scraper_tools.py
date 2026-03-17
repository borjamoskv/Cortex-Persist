"""SCRAPER-Ω MCP Tools — Sovereign Web Extraction for Model Context Protocol.

Exposes scraping capabilities as MCP tools for LLM agents.
"""

from __future__ import annotations

import logging

LOG = logging.getLogger("cortex.mcp.scraper")


def register_scraper_tools(mcp) -> None:
    """Register scraper tools with the MCP server.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.tool()
    async def cortex_scrape(url: str, strategy: str = "auto") -> dict:
        """Extract web content from a URL as clean markdown.

        Supports multiple extraction strategies with automatic fallback:
        - auto: Cascade through all strategies until one succeeds
        - http_fast: Direct HTTP + HTML-to-markdown (fastest, static pages)
        - jina: Jina Reader API (handles JS rendering server-side)
        - firecrawl: Firecrawl API (deep extraction, requires API key)
        - playwright: Full browser rendering (heaviest, for complex SPAs)

        Args:
            url: The URL to scrape.
            strategy: Extraction strategy (auto|http_fast|jina|firecrawl|playwright).

        Returns:
            Dict with url, title, content (markdown), hash, strategy_used, elapsed_ms.
        """
        from cortex.extensions.scraper.engine import ScraperEngine
        from cortex.extensions.scraper.models import ExtractionStrategy, ScrapeRequest

        engine = ScraperEngine()
        request = ScrapeRequest(
            url=url,
            strategy=ExtractionStrategy(strategy),
        )
        result = await engine.scrape(request)

        return {
            "url": result.url,
            "title": result.title,
            "content": result.content,
            "hash": result.content_hash,
            "strategy_used": result.strategy_used.value,
            "elapsed_ms": result.elapsed_ms,
            "status": result.status,
            "error": result.error,
        }

    @mcp.tool()
    async def cortex_scrape_batch(
        urls: list[str],
        strategy: str = "auto",
        concurrency: int = 3,
    ) -> dict:
        """Batch extract web content from multiple URLs.

        Scrapes multiple URLs concurrently with rate limiting and deduplication.

        Args:
            urls: List of URLs to scrape.
            strategy: Extraction strategy for all URLs.
            concurrency: Max concurrent extractions (default: 3).

        Returns:
            Dict with job_id, total, successful, errors, and results list.
        """
        from cortex.extensions.scraper.engine import ScraperEngine
        from cortex.extensions.scraper.models import ExtractionStrategy

        engine = ScraperEngine()
        job = await engine.batch_scrape(
            urls=urls,
            strategy=ExtractionStrategy(strategy),
            concurrency=concurrency,
        )

        return {
            "job_id": job.job_id,
            "total": len(job.urls),
            "successful": job.successful_count,
            "errors": job.error_count,
            "results": [
                {
                    "url": r.url,
                    "title": r.title,
                    "content": r.content[:2000] if r.content else "",
                    "status": r.status,
                    "strategy": r.strategy_used.value,
                    "error": r.error,
                }
                for r in job.results
            ],
        }

    @mcp.tool()
    async def cortex_scrape_map(url: str, depth: int = 2) -> dict:
        """Discover all URLs from a website via link extraction.

        Crawls a site up to the specified depth and returns all discovered URLs.

        Args:
            url: Starting URL.
            depth: Maximum crawl depth (default: 2).

        Returns:
            Dict with url, depth, and discovered_urls list.
        """
        from cortex.extensions.scraper.engine import ScraperEngine

        engine = ScraperEngine()
        discovered = await engine.map_site(url, max_depth=depth)

        return {
            "url": url,
            "depth": depth,
            "total": len(discovered),
            "discovered_urls": discovered,
        }

    LOG.info(
        "🕷️ SCRAPER-Ω MCP tools registered: cortex_scrape, cortex_scrape_batch, cortex_scrape_map"
    )
