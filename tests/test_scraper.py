"""SCRAPER-Ω Unit Tests — Sovereign Web Extraction.

Tests cover:
- HTML-to-Markdown conversion
- ScrapeResult deduplication hash
- HttpExtractor with mocked responses
- Cascade fallback logic
- robots.txt compliance
- Batch scraping
- Rate limiting
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.scraper.extractors import (
    ExtractionError,
    HttpExtractor,
    html_to_markdown,
)
from cortex.scraper.models import (
    ExtractionStrategy,
    JobStatus,
    OutputFormat,
    ScrapeJob,
    ScrapeRequest,
    ScrapeResult,
)

# ==============================================================================
# 1. HTML-to-Markdown Converter
# ==============================================================================


class TestHtmlToMarkdown:
    """Tests for the stdlib HTML→Markdown converter."""

    def test_basic_heading(self):
        html = "<h1>Hello World</h1>"
        _, md = html_to_markdown(html)
        assert "# Hello World" in md

    def test_paragraphs(self):
        html = "<p>First paragraph</p><p>Second paragraph</p>"
        _, md = html_to_markdown(html)
        assert "First paragraph" in md
        assert "Second paragraph" in md

    def test_links(self):
        html = '<a href="https://example.com">Click here</a>'
        _, md = html_to_markdown(html)
        assert "[Click here](https://example.com)" in md

    def test_bold_and_italic(self):
        html = "<strong>bold</strong> and <em>italic</em>"
        _, md = html_to_markdown(html)
        assert "**bold**" in md
        assert "*italic*" in md

    def test_list_items(self):
        html = "<ul><li>Item A</li><li>Item B</li></ul>"
        _, md = html_to_markdown(html)
        assert "- Item A" in md
        assert "- Item B" in md

    def test_script_tags_skipped(self):
        html = "<p>Visible</p><script>alert('x')</script><p>Also visible</p>"
        _, md = html_to_markdown(html)
        assert "Visible" in md
        assert "Also visible" in md
        assert "alert" not in md

    def test_title_extraction(self):
        html = "<html><head><title>My Page</title></head><body><p>Content</p></body></html>"
        title, _ = html_to_markdown(html)
        assert title == "My Page"

    def test_empty_html(self):
        title, md = html_to_markdown("")
        assert title == ""
        assert md == ""

    def test_code_tags(self):
        html = "<code>print('hello')</code>"
        _, md = html_to_markdown(html)
        assert "`print('hello')`" in md


# ==============================================================================
# 2. ScrapeResult Model
# ==============================================================================


class TestScrapeResult:
    """Tests for ScrapeResult data model."""

    def test_compute_hash_deterministic(self):
        """Same content → same hash."""
        hash1 = ScrapeResult.compute_hash("Hello, World!")
        hash2 = ScrapeResult.compute_hash("Hello, World!")
        assert hash1 == hash2
        assert len(hash1) == 16

    def test_compute_hash_different(self):
        """Different content → different hash."""
        hash1 = ScrapeResult.compute_hash("Content A")
        hash2 = ScrapeResult.compute_hash("Content B")
        assert hash1 != hash2

    def test_from_extraction_factory(self):
        result = ScrapeResult.from_extraction(
            url="https://example.com",
            title="Example",
            content="# Example\n\nSome content here.",
            strategy=ExtractionStrategy.HTTP_FAST,
            elapsed_ms=150.0,
        )
        assert result.status == "success"
        assert result.url == "https://example.com"
        assert result.content_hash != ""
        assert result.error is None

    def test_from_error_factory(self):
        result = ScrapeResult.from_error(
            url="https://example.com",
            error="Connection refused",
            strategy=ExtractionStrategy.JINA,
            elapsed_ms=500.0,
        )
        assert result.status == "error"
        assert result.error == "Connection refused"
        assert result.content == ""

    def test_deduplication_same_content(self):
        """Same content produces same hash for dedup detection."""
        content = "# Title\n\nThis is the page content."
        r1 = ScrapeResult.from_extraction(
            url="https://a.com", title="A", content=content,
            strategy=ExtractionStrategy.AUTO, elapsed_ms=100,
        )
        r2 = ScrapeResult.from_extraction(
            url="https://b.com", title="B", content=content,
            strategy=ExtractionStrategy.AUTO, elapsed_ms=200,
        )
        assert r1.content_hash == r2.content_hash


# ==============================================================================
# 3. ScrapeRequest Model
# ==============================================================================


class TestScrapeRequest:
    """Tests for ScrapeRequest model."""

    def test_auto_prefix_url(self):
        """Auto-prefix https:// if missing."""
        req = ScrapeRequest(url="example.com")
        assert req.url == "https://example.com"

    def test_url_already_prefixed(self):
        req = ScrapeRequest(url="https://example.com")
        assert req.url == "https://example.com"

    def test_defaults(self):
        req = ScrapeRequest(url="https://example.com")
        assert req.strategy == ExtractionStrategy.AUTO
        assert req.output_format == OutputFormat.MARKDOWN
        assert req.rate_limit == 1.0
        assert req.respect_robots is True


# ==============================================================================
# 4. ScrapeJob Model
# ==============================================================================


class TestScrapeJob:
    """Tests for ScrapeJob batch model."""

    def test_progress_empty(self):
        job = ScrapeJob(job_id="test", urls=[])
        assert abs(job.progress - 100.0) < 0.01

    def test_progress_partial(self):
        job = ScrapeJob(job_id="test", urls=["a", "b", "c", "d"])
        job.checkpoint_index = 2
        assert abs(job.progress - 50.0) < 0.01

    def test_successful_count(self):
        job = ScrapeJob(job_id="test", urls=["a", "b"])
        job.results = [
            ScrapeResult.from_extraction(
                url="a", title="A", content="content",
                strategy=ExtractionStrategy.AUTO, elapsed_ms=100,
            ),
            ScrapeResult.from_error(
                url="b", error="fail",
                strategy=ExtractionStrategy.AUTO, elapsed_ms=50,
            ),
        ]
        assert job.successful_count == 1
        assert job.error_count == 1


# ==============================================================================
# 5. HttpExtractor (Mocked)
# ==============================================================================


class TestHttpExtractor:
    """Tests for HTTP fast extractor with mocked httpx."""

    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        """Mock a successful HTML response and verify markdown output."""
        html_body = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Title</h1>
            <p>This is a paragraph with enough content to pass the minimum length check
            that the extractor applies to avoid false positives from JS-rendered pages.</p>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_body
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("cortex.scraper.extractors.httpx.AsyncClient", return_value=mock_client):
            extractor = HttpExtractor()
            title, content = await extractor.extract("https://example.com")

        assert title == "Test Page"
        assert "# Main Title" in content
        assert "paragraph" in content

    @pytest.mark.asyncio
    async def test_non_html_content_type(self):
        """Non-HTML content type raises ExtractionError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("cortex.scraper.extractors.httpx.AsyncClient", return_value=mock_client):
            extractor = HttpExtractor()
            with pytest.raises(ExtractionError, match="Non-HTML"):
                await extractor.extract("https://api.example.com/data")


# ==============================================================================
# 6. Robots.txt Compliance
# ==============================================================================


class TestRobotsTxt:
    """Tests for robots.txt compliance checker."""

    @pytest.mark.asyncio
    async def test_allowed_path(self):
        """Path not in Disallow should be allowed."""
        robots_txt = "User-agent: *\nDisallow: /admin/\nDisallow: /private/"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = robots_txt

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from cortex.scraper.extractors import check_robots_txt

        with patch("cortex.scraper.extractors.httpx.AsyncClient", return_value=mock_client):
            result = await check_robots_txt("https://example.com/public/page")

        assert result is True

    @pytest.mark.asyncio
    async def test_blocked_path(self):
        """Path matching Disallow should be blocked."""
        robots_txt = "User-agent: *\nDisallow: /admin/\nDisallow: /private/"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = robots_txt

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from cortex.scraper.extractors import check_robots_txt

        with patch("cortex.scraper.extractors.httpx.AsyncClient", return_value=mock_client):
            result = await check_robots_txt("https://example.com/admin/secret")

        assert result is False

    @pytest.mark.asyncio
    async def test_no_robots_txt(self):
        """Missing robots.txt (404) defaults to allowed."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from cortex.scraper.extractors import check_robots_txt

        with patch("cortex.scraper.extractors.httpx.AsyncClient", return_value=mock_client):
            result = await check_robots_txt("https://example.com/anything")

        assert result is True


# ==============================================================================
# 7. ScraperEngine — Cascade
# ==============================================================================


class TestScraperEngine:
    """Tests for the scraper engine orchestrator."""

    @pytest.mark.asyncio
    async def test_cascade_first_strategy_succeeds(self):
        """If HTTP_FAST works, no fallback needed."""
        from cortex.scraper.engine import ScraperEngine

        engine = ScraperEngine()

        mock_extractor = AsyncMock()
        mock_extractor.extract = AsyncMock(
            return_value=("Test Title", "# Test Content\n\nEnough content to pass checks.")
        )

        with patch.dict("cortex.scraper.extractors.EXTRACTORS", {"http_fast": mock_extractor}):
            with patch("cortex.scraper.extractors.CASCADE_ORDER", ["http_fast"]):
                result = await engine._cascade_extract("https://example.com", 15.0)

        assert result.status == "success"
        assert result.title == "Test Title"

    @pytest.mark.asyncio
    async def test_cascade_fallback(self):
        """If HTTP_FAST fails, cascade to Jina."""
        from cortex.scraper.engine import ScraperEngine

        engine = ScraperEngine()

        mock_http = AsyncMock()
        mock_http.extract = AsyncMock(side_effect=ExtractionError("HTTP failed"))

        mock_jina = AsyncMock()
        mock_jina.extract = AsyncMock(
            return_value=("Jina Title", "# Jina Content\n\nExtracted via Jina Reader.")
        )

        extractors = {"http_fast": mock_http, "jina": mock_jina}
        cascade = ["http_fast", "jina"]

        with patch.dict("cortex.scraper.extractors.EXTRACTORS", extractors, clear=True):
            with patch("cortex.scraper.extractors.CASCADE_ORDER", cascade):
                result = await engine._cascade_extract("https://example.com", 15.0)

        assert result.status == "success"
        assert result.strategy_used == ExtractionStrategy.JINA

    @pytest.mark.asyncio
    async def test_all_strategies_fail(self):
        """If all strategies fail, return error result."""
        from cortex.scraper.engine import ScraperEngine

        engine = ScraperEngine()

        mock_ext = AsyncMock()
        mock_ext.extract = AsyncMock(side_effect=ExtractionError("Failed"))

        with patch.dict(
            "cortex.scraper.extractors.EXTRACTORS", {"http_fast": mock_ext}, clear=True
        ):
            with patch("cortex.scraper.extractors.CASCADE_ORDER", ["http_fast"]):
                result = await engine._cascade_extract("https://example.com", 15.0)

        assert result.status == "error"
        assert "All strategies failed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Verify rate limiting enforces minimum interval."""
        from cortex.scraper.engine import ScraperEngine

        engine = ScraperEngine()
        engine._last_request_time = time.monotonic()

        start = time.monotonic()
        await engine._rate_limit(rate=10.0)  # 10 req/s = 0.1s between
        elapsed = time.monotonic() - start

        # Should have waited ~0.1s (±tolerance for test env)
        assert elapsed >= 0.05  # Generous lower bound for CI

    @pytest.mark.asyncio
    async def test_deduplication_detection(self):
        """Same content hash triggers dedup flag."""
        from cortex.scraper.engine import ScraperEngine

        engine = ScraperEngine()
        content = "# Identical content for dedup test"
        hash_val = ScrapeResult.compute_hash(content)
        engine._seen_hashes.add(hash_val)

        mock_ext = AsyncMock()
        mock_ext.extract = AsyncMock(return_value=("Title", content))

        with (
            patch.dict(
                "cortex.scraper.extractors.EXTRACTORS", {"http_fast": mock_ext}, clear=True
            ),
            patch("cortex.scraper.extractors.CASCADE_ORDER", ["http_fast"]),
            patch("cortex.scraper.extractors.check_robots_txt", return_value=True),
        ):
            request = ScrapeRequest(url="https://example.com")
            result = await engine.scrape(request)

        assert result.metadata.get("deduplicated") is True


# ==============================================================================
# 8. Batch Scraping
# ==============================================================================


class TestBatchScraping:
    """Tests for batch scrape functionality."""

    @pytest.mark.asyncio
    async def test_batch_scrape_multiple_urls(self):
        """Batch scrape processes multiple URLs and returns job."""
        from cortex.scraper.engine import ScraperEngine

        engine = ScraperEngine()

        mock_ext = AsyncMock()
        mock_ext.extract = AsyncMock(
            return_value=("Title", "# Content\n\nSufficient content for batch test completion.")
        )

        with (
            patch.dict(
                "cortex.scraper.extractors.EXTRACTORS", {"http_fast": mock_ext}, clear=True
            ),
            patch("cortex.scraper.extractors.CASCADE_ORDER", ["http_fast"]),
            patch("cortex.scraper.extractors.check_robots_txt", return_value=True),
        ):
            job = await engine.batch_scrape(
                urls=["https://a.com", "https://b.com"],
                concurrency=2,
                rate_limit=100.0,  # High rate for test speed
            )

        assert job.status == JobStatus.COMPLETED
        assert len(job.results) == 2
        assert job.successful_count == 2
        assert job.error_count == 0
