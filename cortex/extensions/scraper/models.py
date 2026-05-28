"""SCRAPER-Ω — Data models for web extraction.

Pydantic-validated schemas for requests, results, and batch jobs.
"""

from __future__ import annotations

import enum
import hashlib
import time
from dataclasses import dataclass, field


class ExtractionStrategy(enum.Enum):
    """Extraction strategy selector."""

    AUTO = "auto"
    HTTP_FAST = "http_fast"
    JINA = "jina"
    FIRECRAWL = "firecrawl"
    PLAYWRIGHT = "playwright"


class OutputFormat(enum.Enum):
    """Output format for extracted content."""

    MARKDOWN = "markdown"
    JSON = "json"
    TEXT = "text"


@dataclass
class ScrapeRequest:
    """Incoming scrape request."""

    url: str
    strategy: ExtractionStrategy = ExtractionStrategy.AUTO
    output_format: OutputFormat = OutputFormat.MARKDOWN
    selectors: list[str] = field(default_factory=list)
    rate_limit: float = 1.0  # requests per second
    respect_robots: bool = True
    timeout: float = 15.0
    max_depth: int = 2

    def __post_init__(self):
        if not self.url or not self.url.startswith(("http://", "https://")):
            if self.url and not self.url.startswith("http"):
                self.url = f"https://{self.url}"


@dataclass
class ScrapeResult:
    """Result from a single URL extraction."""

    url: str
    title: str
    content: str
    content_hash: str
    strategy_used: ExtractionStrategy
    elapsed_ms: float
    status: str = "success"
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def compute_hash(content: str) -> str:
        """SHA-256 content hash for deduplication."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def from_extraction(
        cls,
        url: str,
        title: str,
        content: str,
        strategy: ExtractionStrategy,
        elapsed_ms: float,
        metadata: dict | None = None,
    ) -> ScrapeResult:
        """Factory for successful extractions."""
        return cls(
            url=url,
            title=title,
            content=content,
            content_hash=cls.compute_hash(content),
            strategy_used=strategy,
            elapsed_ms=elapsed_ms,
            metadata=metadata or {},
        )

    @classmethod
    def from_error(
        cls,
        url: str,
        error: str,
        strategy: ExtractionStrategy,
        elapsed_ms: float,
    ) -> ScrapeResult:
        """Factory for failed extractions."""
        return cls(
            url=url,
            title="",
            content="",
            content_hash="",
            strategy_used=strategy,
            elapsed_ms=elapsed_ms,
            status="error",
            error=error,
        )


class JobStatus(enum.Enum):
    """Batch job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class ScrapeJob:
    """Batch scraping job with checkpoint support."""

    job_id: str
    urls: list[str]
    status: JobStatus = JobStatus.PENDING
    results: list[ScrapeResult] = field(default_factory=list)
    checkpoint_index: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    strategy: ExtractionStrategy = ExtractionStrategy.AUTO

    @property
    def progress(self) -> float:
        """Completion percentage."""
        if not self.urls:
            return 100.0
        return (self.checkpoint_index / len(self.urls)) * 100.0

    @property
    def successful_count(self) -> int:
        """Number of successfully scraped URLs."""
        return sum(1 for r in self.results if r.status == "success")

    @property
    def error_count(self) -> int:
        """Number of failed extractions."""
        return sum(1 for r in self.results if r.status == "error")
