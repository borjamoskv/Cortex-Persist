"""SCRAPER-Ω — Sovereign Scraping Engine.

Orchestrates multi-strategy extraction with automatic fallback cascade,
deduplication, rate limiting, and batch processing with checkpoints.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid

from cortex.scraper.extractors import (
    CASCADE_ORDER,
    EXTRACTORS,
    ExtractionError,
    check_robots_txt,
)
from cortex.scraper.models import (
    ExtractionStrategy,
    JobStatus,
    ScrapeJob,
    ScrapeRequest,
    ScrapeResult,
)

LOG = logging.getLogger("cortex.scraper.engine")


class ScraperEngine:
    """Sovereign Scraping Engine — orchestrates extraction strategies.

    Features:
    - Automatic fallback cascade: HTTP → Jina → Firecrawl → Playwright
    - Content deduplication via SHA-256 hash
    - Rate limiting (configurable, default 1 req/sec)
    - Robots.txt compliance
    - Batch processing with checkpoint/resume
    """

    def __init__(self):
        self._seen_hashes: set[str] = set()
        self._last_request_time: float = 0.0
        self._jobs: dict[str, ScrapeJob] = {}

    async def scrape(self, request: ScrapeRequest) -> ScrapeResult:
        """Scrape a single URL with the specified strategy.

        Args:
            request: ScrapeRequest with URL and configuration.

        Returns:
            ScrapeResult with extracted content or error details.
        """
        # Robots.txt compliance
        if request.respect_robots:
            allowed = await check_robots_txt(request.url)
            if not allowed:
                return ScrapeResult.from_error(
                    url=request.url,
                    error="Blocked by robots.txt",
                    strategy=request.strategy,
                    elapsed_ms=0,
                )

        # Rate limiting
        await self._rate_limit(request.rate_limit)

        # Execute extraction
        start = time.monotonic()
        result = await self._execute_strategy(request)
        elapsed_ms = (time.monotonic() - start) * 1000

        if result.status == "success":
            result.elapsed_ms = elapsed_ms
            # Deduplication check
            if result.content_hash in self._seen_hashes:
                LOG.info("♻️ [DEDUP] Content already seen: %s", request.url)
                result.metadata["deduplicated"] = True
            else:
                self._seen_hashes.add(result.content_hash)

        return result

    async def scrape_url(self, url: str, strategy: str = "auto") -> ScrapeResult:
        """Convenience method — scrape a URL with minimal config."""
        strat = ExtractionStrategy(strategy)
        request = ScrapeRequest(url=url, strategy=strat)
        return await self.scrape(request)

    async def batch_scrape(
        self,
        urls: list[str],
        strategy: ExtractionStrategy = ExtractionStrategy.AUTO,
        concurrency: int = 3,
        rate_limit: float = 1.0,
    ) -> ScrapeJob:
        """Batch scrape multiple URLs with concurrency control.

        Args:
            urls: List of URLs to scrape.
            strategy: Extraction strategy to use.
            concurrency: Max concurrent extractions.
            rate_limit: Requests per second.

        Returns:
            ScrapeJob with all results.
        """
        job = ScrapeJob(
            job_id=str(uuid.uuid4())[:8],
            urls=urls,
            status=JobStatus.RUNNING,
            strategy=strategy,
        )
        self._jobs[job.job_id] = job

        LOG.info(
            "📦 [BATCH] Starting job %s — %d URLs, concurrency=%d",
            job.job_id,
            len(urls),
            concurrency,
        )

        semaphore = asyncio.Semaphore(concurrency)

        async def _scrape_one(url: str, index: int) -> ScrapeResult:
            async with semaphore:
                request = ScrapeRequest(
                    url=url,
                    strategy=strategy,
                    rate_limit=rate_limit,
                )
                result = await self.scrape(request)
                job.checkpoint_index = index + 1
                return result

        tasks = [_scrape_one(url, i) for i, url in enumerate(urls)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, ScrapeResult):
                job.results.append(r)
            elif isinstance(r, Exception):
                job.results.append(
                    ScrapeResult.from_error(
                        url="unknown",
                        error=str(r),
                        strategy=strategy,
                        elapsed_ms=0,
                    )
                )

        job.status = JobStatus.COMPLETED
        job.completed_at = time.time()

        LOG.info(
            "✅ [BATCH] Job %s complete — %d/%d successful, %d errors",
            job.job_id,
            job.successful_count,
            len(urls),
            job.error_count,
        )

        return job

    async def map_site(self, url: str, max_depth: int = 2) -> list[str]:
        """Discover URLs from a site via link extraction.

        Args:
            url: Starting URL.
            max_depth: Maximum crawl depth.

        Returns:
            List of discovered URLs.
        """
        LOG.info("🗺️ [MAP] Mapping site: %s (depth=%d)", url, max_depth)

        discovered: set[str] = set()
        to_visit: list[tuple[str, int]] = [(url, 0)]
        visited: set[str] = set()

        from urllib.parse import urljoin, urlparse

        base_domain = urlparse(url).netloc

        while to_visit:
            current_url, depth = to_visit.pop(0)
            if current_url in visited or depth > max_depth:
                continue
            visited.add(current_url)
            discovered.add(current_url)

            # Rate limit
            await self._rate_limit(1.0)

            try:
                import httpx as _httpx

                async with _httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.get(current_url)
                    if response.status_code != 200:
                        continue

                    # Simple link extraction via regex
                    import re

                    links = re.findall(r'href=["\']([^"\']+)["\']', response.text)
                    for link in links:
                        absolute = urljoin(current_url, link)
                        parsed = urlparse(absolute)
                        # Same domain only
                        if parsed.netloc == base_domain and absolute not in visited:
                            to_visit.append((absolute, depth + 1))
                            discovered.add(absolute)

            except (OSError, ValueError):
                continue

        LOG.info("🗺️ [MAP] Discovered %d URLs from %s", len(discovered), url)
        return sorted(discovered)

    def get_job(self, job_id: str) -> ScrapeJob | None:
        """Get a batch job by ID."""
        return self._jobs.get(job_id)

    # ── Internal ──────────────────────────────────────────────────────

    async def _execute_strategy(self, request: ScrapeRequest) -> ScrapeResult:
        """Execute extraction with the configured strategy."""
        start = time.monotonic()

        if request.strategy == ExtractionStrategy.AUTO:
            return await self._cascade_extract(request.url, request.timeout)

        # Specific strategy
        strategy_key = request.strategy.value
        extractor = EXTRACTORS.get(strategy_key)
        if not extractor:
            return ScrapeResult.from_error(
                url=request.url,
                error=f"Unknown strategy: {strategy_key}",
                strategy=request.strategy,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )

        try:
            title, content = await extractor.extract(request.url, request.timeout)
            return ScrapeResult.from_extraction(
                url=request.url,
                title=title,
                content=content,
                strategy=request.strategy,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        except ExtractionError as e:
            return ScrapeResult.from_error(
                url=request.url,
                error=str(e),
                strategy=request.strategy,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )

    async def _cascade_extract(self, url: str, timeout: float) -> ScrapeResult:
        """Try extraction strategies in cascade order until one succeeds."""
        errors: list[str] = []

        for key in CASCADE_ORDER:
            extractor = EXTRACTORS.get(key)
            if not extractor:
                continue

            strategy = ExtractionStrategy(key)
            start = time.monotonic()

            try:
                title, content = await extractor.extract(url, timeout)
                elapsed = (time.monotonic() - start) * 1000
                LOG.info(
                    "✅ [CASCADE] %s succeeded for %s (%.0fms)",
                    key.upper(),
                    url,
                    elapsed,
                )
                return ScrapeResult.from_extraction(
                    url=url,
                    title=title,
                    content=content,
                    strategy=strategy,
                    elapsed_ms=elapsed,
                    metadata={"cascade_attempts": len(errors) + 1},
                )
            except ExtractionError as e:
                elapsed = (time.monotonic() - start) * 1000
                LOG.warning(
                    "⚠️ [CASCADE] %s failed for %s (%.0fms): %s",
                    key.upper(),
                    url,
                    elapsed,
                    e,
                )
                errors.append(f"{key}: {e}")

        # All strategies exhausted
        return ScrapeResult.from_error(
            url=url,
            error=f"All strategies failed: {'; '.join(errors)}",
            strategy=ExtractionStrategy.AUTO,
            elapsed_ms=0,
        )

    async def _rate_limit(self, rate: float) -> None:
        """Enforce rate limiting between requests."""
        if rate <= 0:
            return
        min_interval = 1.0 / rate
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < min_interval:
            wait = min_interval - elapsed
            await asyncio.sleep(wait)
        self._last_request_time = time.monotonic()
