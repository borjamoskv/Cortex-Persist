"""SCRAPER-Ω: Sovereign Web Extraction Engine for CORTEX.

Multi-strategy extraction with automatic fallback cascade,
deduplication, rate limiting, and robots.txt compliance.
"""

from cortex.scraper.models import ExtractionStrategy, ScrapeJob, ScrapeRequest, ScrapeResult

__all__ = [
    "ExtractionStrategy",
    "ScrapeJob",
    "ScrapeRequest",
    "ScrapeResult",
]
