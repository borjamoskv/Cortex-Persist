"""SCRAPER-Ω API Routes — REST endpoints for web extraction.

Endpoints:
    POST /api/scraper/scrape   — Single URL extraction
    POST /api/scraper/batch    — Batch URL extraction
    POST /api/scraper/map      — Site URL discovery
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

LOG = logging.getLogger("cortex.routes.scraper")

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


# ── Request/Response Models ──────────────────────────────────────────


class ScrapeRequestBody(BaseModel):
    """Request body for single URL scrape."""

    url: str = Field(..., description="URL to scrape")
    strategy: str = Field(default="auto", description="Extraction strategy")
    respect_robots: bool = Field(default=True, description="Check robots.txt")
    timeout: float = Field(default=15.0, description="Request timeout in seconds")


class BatchScrapeRequestBody(BaseModel):
    """Request body for batch scraping."""

    urls: list[str] = Field(..., description="List of URLs to scrape")
    strategy: str = Field(default="auto", description="Extraction strategy")
    concurrency: int = Field(default=3, ge=1, le=10, description="Max concurrent requests")
    rate_limit: float = Field(default=1.0, description="Requests per second")


class MapRequestBody(BaseModel):
    """Request body for site mapping."""

    url: str = Field(..., description="Starting URL")
    max_depth: int = Field(default=2, ge=1, le=5, description="Max crawl depth")


class ScrapeResponseItem(BaseModel):
    """Single scrape result in response."""

    url: str
    title: str
    content: str
    hash: str
    strategy_used: str
    elapsed_ms: float
    status: str
    error: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/scrape", response_model=ScrapeResponseItem)
async def scrape_url(body: ScrapeRequestBody) -> dict[str, Any]:
    """Extract content from a single URL."""
    from cortex.scraper.engine import ScraperEngine
    from cortex.scraper.models import ExtractionStrategy, ScrapeRequest

    try:
        strategy = ExtractionStrategy(body.strategy)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400,
            detail=f"Invalid strategy: {body.strategy}. "
            f"Valid: auto, http_fast, jina, firecrawl, playwright",
        )

    engine = ScraperEngine()
    request = ScrapeRequest(
        url=body.url,
        strategy=strategy,
        respect_robots=body.respect_robots,
        timeout=body.timeout,
    )
    result = await engine.scrape(request)

    if result.status == "error":
        raise HTTPException(status_code=422, detail=result.error or "Extraction failed")

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


@router.post("/batch")
async def batch_scrape(body: BatchScrapeRequestBody) -> dict[str, Any]:
    """Batch extract content from multiple URLs."""
    from cortex.scraper.engine import ScraperEngine
    from cortex.scraper.models import ExtractionStrategy

    try:
        strategy = ExtractionStrategy(body.strategy)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400,
            detail=f"Invalid strategy: {body.strategy}",
        )

    if len(body.urls) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 URLs per batch")

    engine = ScraperEngine()
    job = await engine.batch_scrape(
        urls=body.urls,
        strategy=strategy,
        concurrency=body.concurrency,
        rate_limit=body.rate_limit,
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
                "content": r.content[:5000],
                "hash": r.content_hash,
                "strategy_used": r.strategy_used.value,
                "elapsed_ms": r.elapsed_ms,
                "status": r.status,
                "error": r.error,
            }
            for r in job.results
        ],
    }


@router.post("/map")
async def map_site(body: MapRequestBody) -> dict[str, Any]:
    """Discover URLs from a website."""
    from cortex.scraper.engine import ScraperEngine

    engine = ScraperEngine()
    urls = await engine.map_site(body.url, max_depth=body.max_depth)

    return {
        "url": body.url,
        "depth": body.max_depth,
        "total": len(urls),
        "discovered_urls": urls,
    }
